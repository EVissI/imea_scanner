from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from app.config import settings
from typing import List, Optional, Dict
from datetime import datetime
import uuid

class MongoClient:
    def __init__(self, url: str = settings.MONGO_URL):
        self.url = url
        self.client = None
        self.db = None
        self.invoices: AsyncIOMotorCollection = None

    async def connect(self):
        self.client = AsyncIOMotorClient(self.url)
        self.db = self.client.get_database("invoices")
        self.invoices = self.db.get_collection("invoices")
        self.states = self.db.get_collection("states")

    async def close(self):
        if self.client:
            self.client.close()

    async def save_invoice(self, user_id: int, items: List[dict], current_index: int, invoice_text: str, state: str = None) -> str:
        """
        Сохраняет сверку в MongoDB и возвращает её invoice_id.
        """
        invoice_id = str(uuid.uuid4())
        invoice_data = {
            "invoice_id": invoice_id,
            "user_id": user_id,
            "items": items,
            "current_index": current_index,
            "invoice_text": invoice_text,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "state": state or "invoice"
        }
        await self.invoices.insert_one(invoice_data)
        return invoice_id

    async def get_user_invoices(self, user_id: int) -> List[dict]:
        """
        Возвращает список сверек пользователя.
        """
        cursor = self.invoices.find({"user_id": user_id})
        return [invoice async for invoice in cursor]

    async def get_invoice_by_id(self, invoice_id: str) -> Optional[dict]:
        """
        Возвращает сверку по invoice_id.
        """
        return await self.invoices.find_one({"invoice_id": invoice_id})

    async def update_invoice(self, invoice_id: str, items: List[dict], current_index: int, state: str = None):
        """
        Обновляет данные сверки.
        """
        update_data = {
            "items": items,
            "current_index": current_index,
            "updated_at": datetime.utcnow()
        }
        if state:
            update_data["state"] = state
        await self.invoices.update_one(
            {"invoice_id": invoice_id},
            {"$set": update_data}
        )

    async def delete_invoice(self, invoice_id: str):
        """
        Удаляет сверку по invoice_id.
        """
        await self.invoices.delete_one({"invoice_id": invoice_id})

mongo_client = MongoClient(settings.MONGO_URL)