import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

DATA_DIR = os.getenv("DATA_DIR", "/data")
DB_FILE = os.path.join(DATA_DIR, "schedules.json")

class Database:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.db_file = DB_FILE
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database file exists"""
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump({"schedules": [], "next_id": 1}, f)
    
    def add_schedule(self, source_chat_id: int, source_message_id: int, group_id: str, 
                     schedule_time: str, is_scheduled_forward: bool = False) -> int:
        """Add a new schedule and return its ID"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        schedule_id = data["next_id"]
        schedule = {
            "id": schedule_id,
            "source_chat_id": source_chat_id,
            "source_message_id": source_message_id,
            "group_id": group_id,
            "schedule_time": schedule_time,
            "status": "pending",
            "is_scheduled_forward": is_scheduled_forward,
            "created_at": datetime.now().isoformat()
        }
        
        data["schedules"].append(schedule)
        data["next_id"] += 1
        
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return schedule_id
    
    def get_schedule(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        for schedule in data["schedules"]:
            if schedule["id"] == schedule_id:
                return schedule
        return None
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        return data["schedules"]
    
    def get_pending_schedules(self) -> List[Dict[str, Any]]:
        """Get all pending schedules"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        return [s for s in data["schedules"] if s["status"] == "pending"]
    
    def update_status(self, schedule_id: int, status: str):
        """Update schedule status"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        for schedule in data["schedules"]:
            if schedule["id"] == schedule_id:
                schedule["status"] = status
                break
        
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule by ID"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        original_length = len(data["schedules"])
        data["schedules"] = [s for s in data["schedules"] if s["id"] != schedule_id]
        
        if len(data["schedules"]) < original_length:
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        return False
    
    def renumber_schedules(self):
        """Renumber all schedules starting from 1 to eliminate gaps"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        # Only renumber if there are schedules
        if data["schedules"]:
            # Renumber all schedules sequentially
            for idx, schedule in enumerate(data["schedules"], start=1):
                schedule["id"] = idx
            
            # Reset next_id to be one more than the highest ID
            data["next_id"] = len(data["schedules"]) + 1
            
            with open(self.db_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
