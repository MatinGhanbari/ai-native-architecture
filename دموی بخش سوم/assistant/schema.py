"""اعتبارسنجی JSON Schema (زیرمجموعهٔ کوچک، بدون وابستگی بیرونی)."""

ACTION_SCHEMA = {
    "type": "object", "required": ["action"],
    "properties": {
        "action": {"type": "string", "enum": ["retrieve", "tool", "finish", "escalate"]},
        "thought": {"type": "string"},
        "query": {"type": "string"},
        "tool": {"type": "string"},
        "args": {"type": "object"},
        "final": {"type": "object"},
        "reason": {"type": "string"},
    },
}

FINAL_SCHEMA = {
    "type": "object", "required": ["status", "answer", "sources"],
    "properties": {
        "status": {"type": "string", "enum": ["answered", "insufficient_info", "escalated", "refused"]},
        "answer": {"type": "string", "maxLength": 600},
        "sources": {"type": "array", "items": {"type": "string"}},
        "order_id": {"type": ["string", "null"], "pattern": r"^\d{4}$"},
    },
}

QUARANTINE_SCHEMA = {"type": "object", "required": ["answer_text"],
                     "properties": {"answer_text": {"type": "string", "maxLength": 400}}}

TOOL_ARG_SCHEMAS = {
    "get_order_status": {"type": "object", "required": ["order_id"],
                         "properties": {"order_id": {"type": "string", "pattern": r"^\d{4}$"}}},
    "request_refund": {"type": "object", "required": ["order_id"],
                       "properties": {"order_id": {"type": "string", "pattern": r"^\d{4}$"},
                                      "reason": {"type": "string"}}},
}

_TYPES = {"object": dict, "string": str, "array": list, "null": type(None)}

def validate(obj, schema, path="$"):
    import re
    errs = []
    types = schema.get("type")
    if types:
        tl = types if isinstance(types, list) else [types]
        if not any(isinstance(obj, _TYPES[t]) for t in tl):
            return [f"{path}: نوع باید {types} باشد"]
    if isinstance(obj, dict):
        for k in schema.get("required", []):
            if k not in obj:
                errs.append(f"{path}.{k}: فیلد الزامی وجود ندارد")
        for k, sub in schema.get("properties", {}).items():
            if k in obj:
                errs += validate(obj[k], sub, f"{path}.{k}")
    if isinstance(obj, str):
        if "enum" in schema and obj not in schema["enum"]:
            errs.append(f"{path}: مقدار «{obj}» مجاز نیست")
        if "pattern" in schema and not re.match(schema["pattern"], obj):
            errs.append(f"{path}: با الگوی {schema['pattern']} نمی‌خواند")
        if "maxLength" in schema and len(obj) > schema["maxLength"]:
            errs.append(f"{path}: طولانی‌تر از حد مجاز")
    if isinstance(obj, list) and "items" in schema:
        for i, it in enumerate(obj):
            errs += validate(it, schema["items"], f"{path}[{i}]")
    return errs
