# -*- coding: utf-8 -*-
"""
IPTV Dream - History Manager
Zarządzanie historią oglądania
"""

import os
import json
import time
from datetime import datetime, timedelta

class HistoryManager:
    """Menadżer historii oglądania"""
    
    def __init__(self, config_file="/etc/enigma2/iptv_dream_history.json", max_items=1000):
        self.config_file = config_file
        self.max_items = max_items
        self.history = self._load_history()
        
    def _load_history(self):
        """Wczytuje historię z pliku"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"watch_history": [], "resume_points": {}}
        
    def _save_history(self):
        """Zapisuje historię do pliku"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except:
            pass
            
    def add_to_history(self, channel):
        """
        Dodaje kanał do historii
        
        Args:
            channel: Słownik z danymi kanału
        """
        history_item = {
            "channel": channel,
            "watched_at": datetime.now().isoformat(),
            "timestamp": time.time()
        }
        
        # Dodaj na początek listy
        self.history["watch_history"].insert(0, history_item)
        
        # Ogranicz rozmiar historii
        if len(self.history["watch_history"]) > self.max_items:
            self.history["watch_history"] = self.history["watch_history"][:self.max_items]
            
        self._save_history()
        
    def get_recent_history(self, limit=50):
        """
        Zwraca ostatnio oglądane kanały
        
        Args:
            limit: Maksymalna liczba pozycji
            
        Returns:
            Lista ostatnich kanałów
        """
        return self.history["watch_history"][:limit]
        
    def get_history_by_date(self, date):
        """
        Zwraca historię z konkretnej daty
        
        Args:
            date: Data w formacie YYYY-MM-DD
            
        Returns:
            Lista kanałów z danej daty
        """
        items = []
        for item in self.history["watch_history"]:
            watched_date = item["watched_at"][:10]  # Tylko data
            if watched_date == date:
                items.append(item)
        return items
        
    def search_history(self, query):
        """
        Szuka w historii
        
        Args:
            query: Szukana fraza
            
        Returns:
            Lista pasujących pozycji
        """
        results = []
        query_lower = query.lower()
        
        for item in self.history["watch_history"]:
            channel = item["channel"]
            title = channel.get("title", "").lower()
            group = channel.get("group", "").lower()
            
            if query_lower in title or query_lower in group:
                results.append(item)
                
        return results
        
    def clear_history(self):
        """Czyści całą historię"""
        self.history = {"watch_history": [], "resume_points": {}}
        self._save_history()
        
    def set_resume_point(self, channel_id, position):
        """
        Ustawia punkt wznowienia dla kanału
        
        Args:
            channel_id: ID kanału
            position: Pozycja w sekundach
        """
        self.history["resume_points"][channel_id] = {
            "position": position,
            "timestamp": time.time(),
            "updated": datetime.now().isoformat()
        }
        self._save_history()
        
    def get_resume_point(self, channel_id):
        """
        Pobiera punkt wznowienia dla kanału
        
        Args:
            channel_id: ID kanału
            
        Returns:
            Pozycja w sekundach lub None
        """
        if channel_id in self.history["resume_points"]:
            # Sprawdź czy punkt nie jest za stary (max 24h)
            point = self.history["resume_points"][channel_id]
            if time.time() - point["timestamp"] < 24 * 3600:
                return point["position"]
        return None
        
    def remove_resume_point(self, channel_id):
        """
        Usuwa punkt wznowienia
        
        Args:
            channel_id: ID kanału
        """
        if channel_id in self.history["resume_points"]:
            del self.history["resume_points"][channel_id]
            self._save_history()
            
    def get_watch_statistics(self):
        """
        Zwraca statystyki oglądania
        
        Returns:
            Słownik ze statystykami
        """
        if not self.history["watch_history"]:
            return {
                "total_watched": 0,
                "unique_channels": 0,
                "today": 0,
                "this_week": 0,
                "this_month": 0,
                "most_watched_day": "",
                "average_daily": 0
            }
            
        now = datetime.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        total_watched = len(self.history["watch_history"])
        unique_channels = len(set(item["channel"].get("title", "") 
                                 for item in self.history["watch_history"]))
        
        today_count = 0
        week_count = 0
        month_count = 0
        daily_counts = {}
        
        for item in self.history["watch_history"]:
            watched_date = datetime.fromisoformat(item["watched_at"]).date()
            
            if watched_date == today:
                today_count += 1
            if watched_date >= week_ago:
                week_count += 1
            if watched_date >= month_ago:
                month_count += 1
                
            day_key = watched_date.isoformat()
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
            
        most_watched_day = max(daily_counts.items(), key=lambda x: x[1])[0] if daily_counts else ""
        average_daily = total_watched / max(len(daily_counts), 1)
        
        return {
            "total_watched": total_watched,
            "unique_channels": unique_channels,
            "today": today_count,
            "this_week": week_count,
            "this_month": month_count,
            "most_watched_day": most_watched_day,
            "average_daily": round(average_daily, 1)
        }
        
    def export_history(self, format="json"):
        """
        Eksportuje historię
        
        Args:
            format: Format eksportu (json/csv)
            
        Returns:
            Dane do eksportu
        """
        if format == "json":
            return self.history
        elif format == "csv":
            csv = "Data,Kanał,Grupa,URL\n"
            for item in self.history["watch_history"]:
                channel = item["channel"]
                watched = item["watched_at"][:19]  # Bez mikrosekund
                title = channel.get("title", "Unknown")
                group = channel.get("group", "")
                url = channel.get("url", "")
                csv += f"{watched},{title},{group},{url}\n"
            return csv

# Globalna instancja
history_manager = HistoryManager()

def get_history_manager():
    """Zwraca globalną instancję menadżera historii"""
    return history_manager