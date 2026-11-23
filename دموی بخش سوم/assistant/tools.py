"""ابزارها و موتور اجرا (Execution Engine). اصل کمترین دسترسی: ابزار به مشتری احرازهویت‌شده محدود است."""
import json, os, time, uuid

class ToolError(Exception):
    pass

class OrdersDB:
    def __init__(self, path):
        self.rows = json.load(open(path, encoding="utf-8"))

    def by_id(self, oid):
        return next((r for r in self.rows if r["order_id"] == oid), None)

class Tools:
    """customer_id از نشست احرازهویت‌شده می‌آید، نه از مدل؛ مدل نمی‌تواند آن را عوض کند."""
    HIGH_RISK = {"request_refund"}

    def __init__(self, db, customer_id, guards=True, fault=None, approval_mode="deny", queue_path="approval_queue.jsonl"):
        self.db, self.customer_id, self.guards, self.fault = db, customer_id, guards, fault
        self.approval_mode, self.queue_path = approval_mode, queue_path

    def allowed(self):
        names = ["get_order_status", "request_refund"]
        if not self.guards:   # حالت ناامن فقط برای نمایش حمله: ابزار مدیریتی بدون محدودیت در دسترس مدل است
            names.append("list_all_orders")
        return names

    def get_order_status(self, order_id):
        if self.fault == "tool_error":
            time.sleep(0.05)
            raise ToolError("timeout: پایگاه سفارش‌ها پاسخ نداد")
        row = self.db.by_id(order_id)
        if row is None or (self.guards and row["customer_id"] != self.customer_id):
            # پیام یکسان برای «وجود ندارد» و «مال شما نیست» تا وجود سفارش دیگران هم لو نرود
            return {"found": False, "order_id": order_id}
        return {"found": True, "order_id": row["order_id"], "status": row["status"], "eta": row["eta"], "items": row["items"]}

    def list_all_orders(self):
        return {"orders": self.db.rows}

    def request_refund(self, order_id, reason=""):
        row = self.db.by_id(order_id)
        if row is None or row["customer_id"] != self.customer_id:
            return {"found": False, "order_id": order_id}
        ticket = "R-" + uuid.uuid4().hex[:5].upper()
        with open(self.queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ticket": ticket, "order_id": order_id, "customer_id": self.customer_id,
                                "reason": reason, "state": "pending_human"}, ensure_ascii=False) + "\n")
        return {"ticket": ticket, "state": "pending_human"}
