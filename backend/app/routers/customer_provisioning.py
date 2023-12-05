from fastapi import APIRouter

from app.customer_provisioning.routes.provision import customer_provisioning_router

# Instantiate the APIRouter
router = APIRouter()

# Include the Shuffle related routes
router.include_router(customer_provisioning_router, prefix="/customer_provisioning", tags=["Customer Provisioning"])
