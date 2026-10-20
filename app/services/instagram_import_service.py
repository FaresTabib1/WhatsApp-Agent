"""
Service d'import des publications Instagram.

Règles :
  - Import idempotent : (connection_id, external_post_id) UNIQUE en DB.
  - Ne crée jamais de produit automatiquement.
  - Ne confirme jamais un produit automatiquement.
  - Le token est déchiffré ici et ne quitte pas ce service.
  - Les publications existantes ne sont pas modifiées (données commerçant préservées).
  - import_status=failed ne bloque pas l'import des autres publications.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_token
from app.integrations.meta_instagram.client import (
    MetaAPIError,
    RateLimitError,
    TokenExpiredError,
    iter_user_media,
)
from app.models.connection import Connection, ConnectionProvider, ConnectionStatus
from app.models.instagram_post import ImportStatus, InstagramPost


@dataclass
class ImportResult:
    """Résultat d'une synchronisation."""
    connection_id: uuid.UUID
    total_fetched: int        # publications récupérées depuis Meta
    created: int              # nouvelles publications enregistrées
    skipped: int              # publications déjà présentes (idempotence)
    failed: int               # erreurs individuelles non bloquantes
    token_expired: bool = False
    rate_limited: bool = False
    error: str | None = None  # erreur globale non récupérable


class InstagramImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_connection(
        self,
        connection_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> ImportResult:
        """
        Importe les publications du compte Instagram lié à cette connexion.

        Isolation : vérifie que la connexion appartient bien au business_id.
        Retourne un ImportResult même en cas d'erreur partielle.
        """
        # 1. Charger et valider la connexion
        connection = await self._get_validated_connection(connection_id, business_id)
        if connection is None:
            return ImportResult(
                connection_id=connection_id,
                total_fetched=0, created=0, skipped=0, failed=0,
                error="Connection not found or does not belong to this business",
            )

        if connection.provider != ConnectionProvider.instagram:
            return ImportResult(
                connection_id=connection_id,
                total_fetched=0, created=0, skipped=0, failed=0,
                error="Connection is not an Instagram connection",
            )

        if connection.status != ConnectionStatus.active:
            return ImportResult(
                connection_id=connection_id,
                total_fetched=0, created=0, skipped=0, failed=0,
                error=f"Connection status is '{connection.status.value}' — reconnection required",
            )

        # 2. Déchiffrer le token — ne jamais logger ni retourner
        meta = connection.meta or {}
        encrypted_token = meta.get("token_encrypted")
        if not encrypted_token:
            return ImportResult(
                connection_id=connection_id,
                total_fetched=0, created=0, skipped=0, failed=0,
                error="No token found for this connection — reconnection required",
            )

        try:
            plain_token = decrypt_token(encrypted_token)
        except ValueError:
            await self._mark_connection_error(connection)
            return ImportResult(
                connection_id=connection_id,
                total_fetched=0, created=0, skipped=0, failed=0,
                error="Token decryption failed — reconnection required",
            )

        # 3. Importer les publications
        return await self._import_media(connection, plain_token)

    async def _import_media(
        self,
        connection: Connection,
        plain_token: str,
    ) -> ImportResult:
        total = created = skipped = failed = 0

        try:
            async for item in iter_user_media(plain_token):
                total += 1
                try:
                    was_created = await self._upsert_post(connection, item)
                    if was_created:
                        created += 1
                    else:
                        skipped += 1
                except Exception:
                    # Erreur individuelle : continuer l'import
                    failed += 1

        except TokenExpiredError as e:
            await self._mark_connection_error(connection)
            return ImportResult(
                connection_id=connection.id,
                total_fetched=total, created=created,
                skipped=skipped, failed=failed,
                token_expired=True,
                error=str(e),
            )

        except RateLimitError as e:
            return ImportResult(
                connection_id=connection.id,
                total_fetched=total, created=created,
                skipped=skipped, failed=failed,
                rate_limited=True,
                error=str(e),
            )

        except MetaAPIError as e:
            return ImportResult(
                connection_id=connection.id,
                total_fetched=total, created=created,
                skipped=skipped, failed=failed,
                error=str(e),
            )

        return ImportResult(
            connection_id=connection.id,
            total_fetched=total,
            created=created,
            skipped=skipped,
            failed=failed,
        )

    async def _upsert_post(
        self,
        connection: Connection,
        item,
    ) -> bool:
        """
        Crée la publication si elle n'existe pas déjà.
        Retourne True si créée, False si déjà présente.
        Les publications existantes ne sont jamais modifiées
        (préserve les données déjà traitées).
        """
        result = await self.session.execute(
            select(InstagramPost).where(
                InstagramPost.connection_id == connection.id,
                InstagramPost.external_post_id == item.external_post_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            return False  # idempotence — publication déjà importée

        post = InstagramPost(
            business_id=connection.business_id,
            connection_id=connection.id,
            external_post_id=item.external_post_id,
            caption=item.caption,
            media_url=item.media_url,  # éphémère (~1h) — voir modèle
            permalink=item.permalink,
            posted_at=item.posted_at,
            import_status=ImportStatus.pending,
        )
        self.session.add(post)

        try:
            await self.session.flush()  # détecte les violations UNIQUE avant commit
        except IntegrityError:
            await self.session.rollback()
            return False  # race condition — déjà inséré par une autre requête

        await self.session.commit()
        return True

    async def _get_validated_connection(
        self,
        connection_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> Connection | None:
        result = await self.session.execute(
            select(Connection).where(
                Connection.id == connection_id,
                Connection.business_id == business_id,
            )
        )
        return result.scalar_one_or_none()

    async def _mark_connection_error(self, connection: Connection) -> None:
        connection.status = ConnectionStatus.error
        await self.session.commit()
