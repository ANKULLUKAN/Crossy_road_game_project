class EventLogger:

    def log(self, event_name, details=""):
        
        print(f"[EVENT] {event_name} | {details}")