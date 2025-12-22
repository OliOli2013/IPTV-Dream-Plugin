# -*- coding: utf-8 -*-
"""
IPTV Dream - Statistics Manager
Zarządzanie statystykami oglądania
"""

import os
import json
import time
from datetime import datetime, timedelta

class StatisticsManager:
    """Menadżer statystyk oglądania"""
    
    def __init__(self, config_file="/etc/enigma2/iptv_dream_stats.json"):
        self.config_file = config_file
        self.stats = self._load_stats()
        self.current_session = {
            "start_time": time.time(),
            "channels_watched": set(),
            "total_time": 0
        }
        
    def _load_stats(self):
        """Wczytuje statystyki z pliku"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "total_viewing_time": 0,
            "total_channels": 0,
            "most_watched_channels": {},
            "daily_stats": {},
            "hourly_stats": [0] * 24,
            "category_stats": {},
            "monthly_stats": {},
            "first_use": datetime.now().isoformat(),
            "last_use": datetime.now().isoformat()
        }
        
    def _save_stats(self):
        """Zapisuje statystyki do pliku"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except:
            pass
            
    def start_watching(self, channel):
        """
        Rozpoczyna oglądanie kanału
        
        Args:
            channel: Słownik z danymi kanału
        """
        self.current_session["channel_start"] = time.time()
        self.current_session["current_channel"] = channel
        self.current_session["channels_watched"].add(channel.get("title", ""))
        
    def stop_watching(self):
        """Kończy oglądanie i aktualizuje statystyki"""
        if "channel_start" in self.current_session:
            watch_time = time.time() - self.current_session["channel_start"]
            channel = self.current_session.get("current_channel", {})
            
            # Aktualizuj statystyki
            self._update_channel_stats(channel, watch_time)
            self._update_time_stats(watch_time)
            self._update_category_stats(channel, watch_time)
            
            # Wyczyść sesję
            del self.current_session["channel_start"]
            del self.current_session["current_channel"]
            
    def _update_channel_stats(self, channel, watch_time):
        """Aktualizuje statystyki kanału"""
        channel_title = channel.get("title", "Unknown")
        
        if channel_title not in self.stats["most_watched_channels"]:
            self.stats["most_watched_channels"][channel_title] = {
                "total_time": 0,
                "watch_count": 0,
                "last_watched": ""
            }
            
        self.stats["most_watched_channels"][channel_title]["total_time"] += watch_time
        self.stats["most_watched_channels"][channel_title]["watch_count"] += 1
        self.stats["most_watched_channels"][channel_title]["last_watched"] = datetime.now().isoformat()
        
    def _update_time_stats(self, watch_time):
        """Aktualizuje statystyki czasowe"""
        now = datetime.now()
        
        # Dzienny
        day_key = now.strftime("%Y-%m-%d")
        if day_key not in self.stats["daily_stats"]:
            self.stats["daily_stats"][day_key] = 0
        self.stats["daily_stats"][day_key] += watch_time
        
        # Godzinny
        hour = now.hour
        self.stats["hourly_stats"][hour] += watch_time
        
        # Miesięczny
        month_key = now.strftime("%Y-%m")
        if month_key not in self.stats["monthly_stats"]:
            self.stats["monthly_stats"][month_key] = 0
        self.stats["monthly_stats"][month_key] += watch_time
        
        # Całkowity czas
        self.stats["total_viewing_time"] += watch_time
        self.stats["last_use"] = now.isoformat()
        
    def _update_category_stats(self, channel, watch_time):
        """Aktualizuje statystyki kategorii"""
        category = channel.get("group", "Inne")
        
        if category not in self.stats["category_stats"]:
            self.stats["category_stats"][category] = {
                "total_time": 0,
                "channels": {}
            }
            
        self.stats["category_stats"][category]["total_time"] += watch_time
        
        channel_title = channel.get("title", "Unknown")
        if channel_title not in self.stats["category_stats"][category]["channels"]:
            self.stats["category_stats"][category]["channels"][channel_title] = 0
        self.stats["category_stats"][category]["channels"][channel_title] += watch_time
        
    def get_stats(self, lang="pl"):
        """
        Zwraca kompletne statystyki
        
        Returns:
            Słownik ze statystykami
        """
        # Oblicz dodatkowe statystyki
        total_days = len(self.stats["daily_stats"])
        avg_daily = self.stats["total_viewing_time"] / max(total_days, 1)
        
        # Najczęściej oglądane kanały
        top_channels = sorted(
            self.stats["most_watched_channels"].items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )[:10]
        
        # Najczęściej oglądane kategorie
        top_categories = sorted(
            self.stats["category_stats"].items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )[:10]
        
        # Godziny szczytu
        peak_hours = sorted(
            [(i, self.stats["hourly_stats"][i]) for i in range(24)],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        hours_word = 'godzin' if lang == 'pl' else 'hours'
        def t(pl, en):
            return pl if lang == 'pl' else en
        # Normalize common Polish default group name for EN display
        def norm_group(name):
            if lang != 'pl' and name == 'Inne':
                return 'Other'
            return name
        top_channels_fmt = [(name, data) for name, data in top_channels[:5]]
        top_categories_fmt = [(norm_group(name), data) for name, data in top_categories[:5]]
        peak_hours_fmt = peak_hours[:3]
        monthly_fmt = sorted(self.stats['monthly_stats'].items(), reverse=True)[:3]
        return [
            (t('📊 Podsumowanie', '📊 Summary'), ''),
            (t('Całkowity czas', 'Total time'), f"{self.stats['total_viewing_time'] / 3600:.1f} {hours_word}"),
            (t('Średnio dziennie', 'Average per day'), f"{avg_daily / 3600:.1f} {hours_word}"),
            (t('Ilość dni', 'Days'), total_days),
            (t('Obejrzane kanały', 'Watched channels'), len(self.stats['most_watched_channels'])),
            (t('Kategorie', 'Categories'), len(self.stats['category_stats'])),
            (t('Ostatnie użycie', 'Last use'), self.stats['last_use'][:10]),
            ('', ''),
            (t('📺 TOP 5 Kanałów', '📺 TOP 5 Channels'), ''),
            *[(f"{i+1}. {name}", f"{data['total_time']/3600:.1f}h ({data['watch_count']}x)") for i, (name, data) in enumerate(top_channels_fmt)],
            ('', ''),
            (t('🏷️ TOP 5 Kategorii', '🏷️ TOP 5 Categories'), ''),
            *[(f"{i+1}. {name}", f"{data['total_time']/3600:.1f}h") for i, (name, data) in enumerate(top_categories_fmt)],
            ('', ''),
            (t('⏰ Godziny szczytu', '⏰ Peak hours'), ''),
            *[(f"{hour:02d}:00", f"{tm/3600:.1f}h") for hour, tm in peak_hours_fmt],
            ('', ''),
            (t('📈 Miesięczne', '📈 Monthly'), ''),
            *[(month, f"{tm/3600:.1f}h") for month, tm in monthly_fmt],
        ]
        
    def get_daily_stats(self, days=7):
        """
        Zwraca statystyki dzienne
        
        Args:
            days: Liczba dni do wstecz
            
        Returns:
            Słownik ze statystykami dziennymi
        """
        daily = {}
        today = datetime.now()
        
        for i in range(days):
            date = today - timedelta(days=i)
            day_key = date.strftime("%Y-%m-%d")
            daily[day_key] = self.stats["daily_stats"].get(day_key, 0)
            
        return daily
        
    def reset_stats(self):
        """Resetuje wszystkie statystyki"""
        self.stats = {
            "total_viewing_time": 0,
            "total_channels": 0,
            "most_watched_channels": {},
            "daily_stats": {},
            "hourly_stats": [0] * 24,
            "category_stats": {},
            "monthly_stats": {},
            "first_use": datetime.now().isoformat(),
            "last_use": datetime.now().isoformat()
        }
        self._save_stats()
        
    def export_stats(self, format="json"):
        """
        Eksportuje statystyki
        
        Args:
            format: Format eksportu (json/csv)
            
        Returns:
            Dane do eksportu
        """
        if format == "json":
            return self.stats
        elif format == "csv":
            # Prosty eksport CSV
            csv = "Kanał,Czas (s),Ilość,Ostatnio\n"
            for name, data in self.stats["most_watched_channels"].items():
                csv += f"{name},{data['total_time']},{data['watch_count']},{data['last_watched']}\n"
            return csv

# Globalna instancja
stats_manager = StatisticsManager()

def get_statistics_manager():
    """Zwraca globalną instancję menadżera statystyk"""
    return stats_manager