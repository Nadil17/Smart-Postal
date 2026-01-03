from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import secrets
from pydantic import BaseModel
from models.database import get_db
from models.user import User, UserRole
from models.order import Order, OrderStatus
from api.schemas import (
    OrderCreate, OrderResponse, OrderUpdate,
    CourierAssignment, OrderFilter
)
from api.middleware.auth import (
    get_current_user, get_current_customer,
    get_current_courier, get_current_admin
)

# Import blockchain services for COD recording
try:
    from utils.blockchain import CryptographicCommitmentEngine, BlockchainService
    BLOCKCHAIN_AVAILABLE = True
except ImportError:
    BLOCKCHAIN_AVAILABLE = False

router = APIRouter(prefix="/api/orders", tags=["Orders"])

# COD Completion Request Schema
class CODCompletionRequest(BaseModel):
    amount_collected: float
    payment_method: str = "cash"  # cash, card, mobile
    courier_notes: Optional[str] = None

router = APIRouter(prefix="/api/orders", tags=["Orders"])

def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"ORD-{timestamp}-{random_part}"

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """Create a new order (Customer only)"""
    
    # Generate unique order number
    order_number = generate_order_number()
    
    # Create order
    new_order = Order(
        order_number=order_number,
        customer_id=current_user.id,
        delivery_address=order_data.delivery_address,
        delivery_city=order_data.delivery_city,
        delivery_postal_code=order_data.delivery_postal_code,
        delivery_instructions=order_data.delivery_instructions,
        total_amount=order_data.total_amount,
        verification_required=order_data.verification_required,
        status=OrderStatus.PENDING
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    return new_order

@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    status: OrderStatus = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List orders based on user role"""
    
    query = db.query(Order)
    
    # Filter based on user role
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Order.customer_id == current_user.id)
    elif current_user.role == UserRole.COURIER:
        # Couriers can see: their assigned orders OR unassigned pending orders
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Order.courier_id == current_user.id,
                Order.courier_id == None  # Unassigned orders
            )
        )
    # Admin can see all orders
    
    # Apply status filter
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get order by ID"""
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check authorization
    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )
    elif current_user.role == UserRole.COURIER:
        # Couriers can view their assigned orders OR unassigned orders
        if order.courier_id is not None and order.courier_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this order"
            )
    
    return order

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update order"""
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Authorization checks
    if current_user.role == UserRole.CUSTOMER:
        # Customers can only update their own orders and only certain fields
        if order.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this order"
            )
        # Customers can only update delivery instructions
        if order_update.delivery_instructions:
            order.delivery_instructions = order_update.delivery_instructions
    
    elif current_user.role == UserRole.COURIER:
        # Couriers can update status of assigned orders
        if order.courier_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this order"
            )
        if order_update.status:
            order.status = order_update.status
            if order_update.status == OrderStatus.DELIVERED:
                order.delivered_at = datetime.now()
    
    elif current_user.role == UserRole.ADMIN:
        # Admin can update everything
        if order_update.status:
            order.status = order_update.status
        if order_update.courier_id:
            order.courier_id = order_update.courier_id
        if order_update.delivery_instructions:
            order.delivery_instructions = order_update.delivery_instructions
    
    db.commit()
    db.refresh(order)
    return order

@router.post("/assign-courier", response_model=OrderResponse)
async def assign_courier(
    assignment: CourierAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Assign courier to order (Admin only)"""
    
    order = db.query(Order).filter(Order.id == assignment.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Verify courier exists and has correct role
    courier = db.query(User).filter(
        User.id == assignment.courier_id,
        User.role == UserRole.COURIER
    ).first()
    if not courier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Courier not found"
        )
    
    order.courier_id = assignment.courier_id
    order.status = OrderStatus.IN_TRANSIT
    
    db.commit()
    db.refresh(order)
    return order

@router.get("/{order_id}/biometric-status")
async def get_biometric_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get biometric enrollment status for an order"""
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Authorization check
    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )
    
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "voice_enrolled": order.voice_enrolled,
        "fingerprint_enrolled": order.fingerprint_enrolled,
        "verification_required": order.verification_required,
        "biometric_enrollment_complete": order.voice_enrolled or order.fingerprint_enrolled
    }

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel an order"""
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Only customer or admin can cancel
    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this order"
        )
    
    # Can't cancel if already delivered or in delivery
    if order.status in [OrderStatus.DELIVERED, OrderStatus.OUT_FOR_DELIVERY]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel order in current status"
        )
    
    order.status = OrderStatus.CANCELLED
    db.commit()
    
    return None

@router.post("/{order_id}/complete-cod")
async def complete_cod_delivery(
    order_id: int,
    cod_data: CODCompletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_courier)
):
    """
    Complete a COD (Cash on Delivery) order with blockchain recording.
    Records payment transaction on blockchain for audit trail.
    """
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Verify courier is assigned to this order
    if order.courier_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete this order"
        )
    
    # Verify order is in correct status
    if order.status not in [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.IN_TRANSIT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete order in status: {order.status}"
        )
    
    blockchain_proof = None
    
    # Record COD on blockchain if available
    if BLOCKCHAIN_AVAILABLE:
        try:
            commitment_engine = CryptographicCommitmentEngine()
            blockchain_service = BlockchainService()
            
            # Prepare COD transaction data
            cod_evidence = {
                "order_id": order.id,
                "order_number": order.order_number,
                "amount_expected": float(order.total_amount),
                "amount_collected": cod_data.amount_collected,
                "payment_method": cod_data.payment_method,
                "courier_id": current_user.id,
                "courier_email": current_user.email,
                "customer_id": order.customer_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate cryptographic commitment
            commitment = commitment_engine.generate_commitment(cod_evidence)
            
            # Record on blockchain
            result = await blockchain_service.record_cod_transaction(
                delivery_id=order.order_number,
                amount=cod_data.amount_collected,
                commitment_hash=commitment["commitment_hash"],
                metadata={
                    "payment_method": cod_data.payment_method,
                    "order_id": order.id,
                    "courier_notes": cod_data.courier_notes
                }
            )
            
            if result.get("success"):
                blockchain_proof = {
                    "block_number": result.get("block_number"),
                    "transaction_hash": result.get("transaction_hash"),
                    "commitment_hash": commitment["commitment_hash"],
                    "proof_type": "cod_transaction"
                }
                
        except Exception as e:
            # Log error but don't fail the transaction
            print(f"Blockchain COD recording failed: {e}")
    
    # Update order status
    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now()
    
    db.commit()
    db.refresh(order)
    
    return {
        "success": True,
        "message": "COD delivery completed successfully",
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status.value,
            "amount_collected": cod_data.amount_collected,
            "delivered_at": order.delivered_at.isoformat()
        },
        "blockchain_proof": blockchain_proof
    }

# Neighbor Consent Request Schema
class NeighborConsentRequest(BaseModel):
    neighbor_name: str
    neighbor_address: str
    neighbor_phone: Optional[str] = None
    consent_type: str = "receive_delivery"  # receive_delivery, hold_package
    photo_proof: Optional[str] = None  # Base64 encoded photo

@router.post("/{order_id}/neighbor-consent")
async def record_neighbor_consent(
    order_id: int,
    consent_data: NeighborConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_courier)
):
    """
    Record neighbor consent for package delivery on blockchain.
    Used when recipient is not available and neighbor agrees to receive.
    """
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Verify courier is assigned to this order
    if order.courier_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to handle this order"
        )
    
    blockchain_proof = None
    
    # Record consent on blockchain if available
    if BLOCKCHAIN_AVAILABLE:
        try:
            commitment_engine = CryptographicCommitmentEngine()
            blockchain_service = BlockchainService()
            
            # Prepare consent evidence
            consent_evidence = {
                "order_id": order.id,
                "order_number": order.order_number,
                "original_recipient_id": order.customer_id,
                "neighbor_name": consent_data.neighbor_name,
                "neighbor_address": consent_data.neighbor_address,
                "consent_type": consent_data.consent_type,
                "courier_id": current_user.id,
                "courier_email": current_user.email,
                "timestamp": datetime.now().isoformat(),
                "has_photo_proof": consent_data.photo_proof is not None
            }
            
            # Generate cryptographic commitment
            commitment = commitment_engine.generate_commitment(consent_evidence)
            
            # Record on blockchain
            result = await blockchain_service.record_neighbor_consent(
                delivery_id=order.order_number,
                neighbor_hash=commitment_engine.generate_commitment({
                    "name": consent_data.neighbor_name,
                    "address": consent_data.neighbor_address
                })["commitment_hash"][:20],  # Shortened for privacy
                consent_commitment=commitment["commitment_hash"],
                metadata={
                    "consent_type": consent_data.consent_type,
                    "order_id": order.id
                }
            )
            
            if result.get("success"):
                blockchain_proof = {
                    "block_number": result.get("block_number"),
                    "transaction_hash": result.get("transaction_hash"),
                    "commitment_hash": commitment["commitment_hash"],
                    "proof_type": "neighbor_consent"
                }
                
        except Exception as e:
            # Log error but don't fail the transaction
            print(f"Blockchain consent recording failed: {e}")
    
    # Update order with delivery notes
    if order.delivery_instructions:
        order.delivery_instructions += f"\n[NEIGHBOR DELIVERY: {consent_data.neighbor_name}]"
    else:
        order.delivery_instructions = f"[NEIGHBOR DELIVERY: {consent_data.neighbor_name}]"
    
    db.commit()
    db.refresh(order)
    
    return {
        "success": True,
        "message": "Neighbor consent recorded successfully",
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "neighbor_name": consent_data.neighbor_name
        },
        "blockchain_proof": blockchain_proof,
        "legal_notice": "Consent recorded per Sri Lanka PDPA Article 5 - Lawful Processing"
    }