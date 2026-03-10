import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

DB_FILE = "schedules.json"

class Database:
    def __init__(self):
        self.db_file = DB_FILE
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database file exists"""
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump({"schedules": [], "next_id": 1}, f)
    
    def add_schedule(self, message_type: str, message_content: str, group_id: str, 
                     schedule_time: str, forward_sender_name: Optional[str] = None,
                     file_id: Optional[str] = None) -> int:
        """Add a new schedule and return its ID"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        schedule_id = data["next_id"]
        schedule = {
            "id": schedule_id,
            "message_type": message_type,
            "message_content": message_content,
            "file_id": file_id,
            "group_id": group_id,
            "schedule_time": schedule_time,
            "status": "pending",
            "forward_sender_name": forward_sender_name,
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
