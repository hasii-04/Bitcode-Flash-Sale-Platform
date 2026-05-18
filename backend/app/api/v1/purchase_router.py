from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.domain.schemas import OrderActionResponse, PurchaseRequest, PurchaseResponse
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

@router.post("/{order_id}/confirm", response_model=OrderActionResponse)
async def confirm_purchase(order_id: int, current_user: User = Depends(get_current_user)):
    order = await PurchaseService.confirm_order(order_id, current_user.id)
    return {
        "success": True,
        "message": "Purchase confirmed successfully.",
        "order_id": order.id,
        "status": order.status,
    }

@router.post("/{order_id}/cancel", response_model=OrderActionResponse)
async def cancel_purchase(order_id: int, current_user: User = Depends(get_current_user)):
    order, _remaining_stock = await PurchaseService.cancel_order(order_id, current_user.id)
    return {
        "success": True,
        "message": "Reservation cancelled and stock released.",
        "order_id": order.id,
        "status": order.status,
    }
