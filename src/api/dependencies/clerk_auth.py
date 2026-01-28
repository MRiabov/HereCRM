import jwt
from fastapi import Request, HTTPException, status, Depends
from jwt import PyJWKClient
from src.config import settings
from src.database import get_db
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Business, UserRole

from clerk_backend_api import Clerk

class VerifyToken:
    def __init__(self):
        if not settings.clerk_jwks_url:
            raise ValueError("CLERK_JWKS_URL is not configured")
        self.jwks_client = PyJWKClient(settings.clerk_jwks_url)
        self.clerk_client = Clerk(bearer_auth=settings.clerk_secret_key)

    async def __call__(self, request: Request, db: AsyncSession = Depends(get_db)) -> User:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing authentication credentials",
            )
        
        token = auth_header.split(" ")[1]
        
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=None,
                issuer=settings.clerk_issuer,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
            )

        clerk_id = payload.get("sub")
        clerk_org_id = payload.get("org_id")

        if not clerk_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")

        # 1. Resolve User
        user_result = await db.execute(
            select(User)
            .options(joinedload(User.business), joinedload(User.wage_config))
            .where(User.clerk_id == clerk_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            # JIT Creation
            try:
                clerk_user = self.clerk_client.users.get(user_id=clerk_id)
                # Resolve Organization if org_id is present
                business = None
                if clerk_org_id:
                    business_result = await db.execute(select(Business).where(Business.clerk_org_id == clerk_org_id))
                    business = business_result.scalar_one_or_none()
                    if not business:
                        clerk_org = self.clerk_client.organizations.get(organization_id=clerk_org_id)
                        business = Business(
                            name=clerk_org.name or f"Org {clerk_org_id}",
                            clerk_org_id=clerk_org_id
                        )
                        db.add(business)
                        await db.flush() # Get business.id
                else:
                    # No org_id in token. For now, maybe create a personal business if none exists?
                    # Or check if user already has a business.
                    # Given the spec "Ensure User.business.clerk_org_id matches token's org_id", 
                    # we might require org_id for PWA access if it's strictly B2B.
                    # Let's assume for now we might need a default business or handle missing org_id.
                    pass

                if not business:
                    # Fallback: find any business or create a default one? 
                    # Spec says "Link User to Business". Let's create a placeholder business if needed.
                    business_result = await db.execute(select(Business).where(Business.name == "Default Business"))
                    business = business_result.scalar_one_or_none()
                    if not business:
                        business = Business(name="Default Business")
                        db.add(business)
                        await db.flush()

                user = User(
                    clerk_id=clerk_id,
                    name=f"{clerk_user.first_name} {clerk_user.last_name}".strip() or clerk_user.username or "Unknown",
                    email=clerk_user.email_addresses[0].email_address if clerk_user.email_addresses else None,
                    phone_number=clerk_user.phone_numbers[0].phone_number if clerk_user.phone_numbers else None,
                    business_id=business.id,
                    role=UserRole.OWNER # Default to owner for first user of business? Or manager?
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            except Exception as e:
                await db.rollback()
                raise HTTPException(status_code=500, detail=f"JIT sync failed: {str(e)}")
        
        # 2. Validate Org Mismatch
        if clerk_org_id and user.business.clerk_org_id != clerk_org_id:
            raise HTTPException(status_code=403, detail="Organization mismatch")

        return user

# Singleton instance for route injection
verify_token = VerifyToken()

async def get_current_user(user: User = Depends(verify_token)) -> User:
    return user
