from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.domain.schemas import PurchaseRequest, PurchaseResponse
from app.domain.models import User
from app.api.dependencies import get_current_user
from app.services.purchase_service import PurchaseService

router = APIRouter()

@router.post("", response_model=PurchaseResponse)
async def purchase_item(
    request: PurchaseRequest, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    High-concurrency endpoint to purchase an item. 
    Offloads to Redis to guarantee zero overselling.
    """
    result = await PurchaseService.process_purchase(request.event_id, request.item_id, current_user.id, background_tasks)
    
    if not result["success"]:
        raise HTTPException(status_code=result["status_code"], detail=result["message"])
        
    return result
