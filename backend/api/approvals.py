from fastapi import APIRouter, HTTPException
import policy.store as store

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("/{approval_id}/resolve")
async def resolve_approval(approval_id: str, approved: bool = True):
    result = store.resolve_approval(approval_id, approved)
    if not result:
        raise HTTPException(status_code=404, detail="Pending approval not found or already resolved")
    return {"id": approval_id, "approved": approved}
