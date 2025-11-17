import sys
import io

# Windows için UTF-8 kodlama zorla
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import time

class LongShortMaxPainCalculator:
    """
    Deribit'ten Long ve Short pozisyonları için ayrı ayrı 
    Max Pain seviyelerini hesaplar
    """
    
    def __init__(self):
        self.base_url = "https://www.deribit.com/api/v2/public"
        self.currency = "BTC"
        print("🔧 Long/Short Max Pain Calculator başlatıldı")
        print(f"📡 API URL: {self.base_url}")
        print()
        
    def get_current_price(self):
        """Mevcut BTC fiyatını al"""
        try:
            print("💰 Mevcut BTC fiyatı çekiliyor...")
            url = f"{self.base_url}/get_index_price"
            params = {"index_name": "btc_usd"}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ API Hatası: {response.status_code}")
                return None
                
            data = response.json()
            price = data['result']['index_price']
            print(f"✅ Mevcut fiyat: ${price:,.2f}")
            return price
            
        except Exception as e:
            print(f"❌ Fiyat alınamadı: {e}")
            return None
    
    def get_all_options(self):
        """Tüm opsiyon kontratlarını getir"""
        try:
            print("📊 Opsiyon kontratları çekiliyor...")
            url = f"{self.base_url}/get_book_summary_by_currency"
            params = {
                "currency": self.currency,
                "kind": "option"
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ API Hatası: {response.status_code}")
                return []
            
            data = response.json()
            
            if 'result' not in data:
                print(f"❌ Beklenmeyen API yanıtı: {data}")
                return []
            
            options = data['result']
            print(f"✅ {len(options)} opsiyon kontratı bulundu")
            return options
            
        except Exception as e:
            print(f"❌ Opsiyon verileri alınamadı: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def parse_instrument(self, instrument_name):
        """
        Instrument adını parse et
        Format: BTC-DDMMMYY-STRIKE-C/P
        Örnek: BTC-29NOV24-95000-C
        """
        try:
            parts = instrument_name.split('-')
            if len(parts) != 4:
                return None
            
            expiry_str = parts[1]
            strike = float(parts[2])
            option_type = parts[3]  # 'C' veya 'P'
            
            # Tarihi parse et
            expiry_date = datetime.strptime(expiry_str, '%d%b%y')
            
            return {
                'expiry': expiry_date,
                'expiry_str': expiry_str,
                'strike': strike,
                'type': option_type
            }
        except Exception as e:
            return None
    
    def calculate_long_short_maxpain(self, options_data, target_expiry):
        """
        Belirli bir vade için Long ve Short max pain'i ayrı hesapla
        
        LONG MAX PAIN: Call opsiyonlarına göre
        SHORT MAX PAIN: Put opsiyonlarına göre
        """
        # Vadeye göre filtrele
        expiry_options = [
            opt for opt in options_data 
            if opt['expiry'] == target_expiry
        ]
        
        if not expiry_options:
            return None, None
        
        # Strike fiyatlarını topla
        strikes = sorted(set(opt['strike'] for opt in expiry_options))
        
        if not strikes:
            return None, None
        
        # LONG MAX PAIN (Call options)
        min_long_pain = float('inf')
        long_max_pain = None
        
        # SHORT MAX PAIN (Put options)
        min_short_pain = float('inf')
        short_max_pain = None
        
        for test_strike in strikes:
            long_pain = 0
            short_pain = 0
            
            for opt in expiry_options:
                strike = opt['strike']
                oi = opt['open_interest']
                opt_type = opt['type']
                
                if opt_type == 'C':  # Call (Long pozisyonlar)
                    intrinsic = max(0, test_strike - strike)
                    long_pain += intrinsic * oi
                    
                else:  # Put (Short pozisyonlar)
                    intrinsic = max(0, strike - test_strike)
                    short_pain += intrinsic * oi
            
            # Long max pain'i bul
            if long_pain < min_long_pain:
                min_long_pain = long_pain
                long_max_pain = test_strike
            
            # Short max pain'i bul
            if short_pain < min_short_pain:
                min_short_pain = short_pain
                short_max_pain = test_strike
        
        return long_max_pain, short_max_pain
    
    def get_target_expiry(self, all_expiries, timeframe_hours):
        """Belirli bir zaman dilimine en yakın vadeyi bul"""
        now = datetime.now()
        target_date = now + timedelta(hours=timeframe_hours)
        
        if not all_expiries:
            return None
        
        # En yakın vadeyi bul
        closest_expiry = min(
            all_expiries,
            key=lambda x: abs((x - target_date).total_seconds())
        )
        
        return closest_expiry
    
    def calculate_all_timeframes(self):
        """Tüm zaman dilimleri için Long/Short max pain hesapla"""
        
        print("=" * 70)
        print("🔄 Deribit'ten Long/Short Max Pain Verileri Çekiliyor...")
        print("=" * 70)
        print()
        
        # Mevcut fiyat
        current_price = self.get_current_price()
        if not current_price:
            print("❌ Fiyat alınamadığı için devam edilemiyor")
            return None
        
        print()
        
        # Tüm opsiyonları çek
        all_options = self.get_all_options()
        if not all_options:
            print("❌ Opsiyon verileri alınamadığı için devam edilemiyor")
            return None
        
        print()
        print("🔄 Veriler işleniyor...")
        
        # Parse et
        options_data = []
        parse_errors = 0
        
        for opt in all_options:
            parsed = self.parse_instrument(opt['instrument_name'])
            if parsed:
                options_data.append({
                    'expiry': parsed['expiry'],
                    'expiry_str': parsed['expiry_str'],
                    'strike': parsed['strike'],
                    'type': parsed['type'],
                    'open_interest': opt.get('open_interest', 0),
                    'volume': opt.get('volume', 0)
                })
            else:
                parse_errors += 1
        
        print(f"✅ {len(options_data)} kontrat başarıyla işlendi")
        if parse_errors > 0:
            print(f"⚠️  {parse_errors} kontrat parse edilemedi")
        
        if not options_data:
            print("❌ İşlenebilir veri bulunamadı")
            return None
        
        # Tüm vadeleri bul
        all_expiries = sorted(set(opt['expiry'] for opt in options_data))
        print(f"📅 {len(all_expiries)} farklı vade tarihi bulundu")
        print()
        
        # Zaman dilimleri (saat cinsinden)
        timeframes = {
            '12H': 12,
            '24H': 24,
            '48H': 48,
            '3D': 72,
            '1W': 168,
            '2W': 336,
            '1M': 720
        }
        
        results = {
            'timestamp': int(datetime.now().timestamp()),
            'current_price': current_price,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timeframes': {}
        }
        
        print("📈 MAX PAIN HESAPLAMALARI (LONG vs SHORT)")
        print("=" * 70)
        print(f"{'Süre':<6} {'Long Max Pain':<18} {'Short Max Pain':<18} {'Vade':<12}")
        print("-" * 70)
        
        for tf_name, hours in timeframes.items():
            # En yakın vadeyi bul
            target_expiry = self.get_target_expiry(all_expiries, hours)
            
            if target_expiry:
                # Long ve Short max pain hesapla
                long_mp, short_mp = self.calculate_long_short_maxpain(
                    options_data, target_expiry
                )
                
                if long_mp and short_mp:
                    days_until = (target_expiry - datetime.now()).days
                    
                    long_dist = ((long_mp - current_price) / current_price) * 100
                    short_dist = ((short_mp - current_price) / current_price) * 100
                    
                    results['timeframes'][tf_name] = {
                        'long_maxpain': long_mp,
                        'short_maxpain': short_mp,
                        'long_distance_pct': long_dist,
                        'short_distance_pct': short_dist,
                        'expiry_date': target_expiry.strftime('%Y-%m-%d'),
                        'days_until': days_until
                    }
                    
                    long_arrow = "↑" if long_dist > 0 else "↓"
                    short_arrow = "↑" if short_dist > 0 else "↓"
                    
                    print(f"{tf_name:<6} "
                          f"${long_mp:>9,.0f} {long_arrow}{abs(long_dist):>5.2f}%   "
                          f"${short_mp:>9,.0f} {short_arrow}{abs(short_dist):>5.2f}%   "
                          f"{days_until}gün")
                else:
                    print(f"{tf_name:<6} Hesaplanamadı (yetersiz veri)")
        
        print("=" * 70)
        print()
        return results
    
    def export_to_json(self, filename="data/maxpain_longshort.json"):
        """JSON olarak kaydet"""
        results = self.calculate_all_timeframes()
        
        if results:
            import os
            os.makedirs('data', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Veriler '{filename}' dosyasına kaydedildi")
            return results
        else:
            print("❌ Kaydedilecek veri yok")
            return None
    
    def export_tradingview_format(self, filename="data/tradingview_format.txt"):
        """TradingView için format"""
        results = self.calculate_all_timeframes()
        
        if results:
            import os
            os.makedirs('data', exist_ok=True)
            
            lines = [
                "# BTC Long/Short Max Pain Levels",
                f"# Updated: {results['update_time']}",
                f"# Current Price: ${results['current_price']:,.2f}",
                "",
                "# Format: TIMEFRAME_LONG=PRICE",
                "#         TIMEFRAME_SHORT=PRICE",
                ""
            ]
            
            for tf, data in results['timeframes'].items():
                lines.append(f"{tf}_LONG={data['long_maxpain']:.0f}")
                lines.append(f"{tf}_SHORT={data['short_maxpain']:.0f}")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print(f"✅ TradingView formatı '{filename}' oluşturuldu")
            return True
        else:
            print("❌ Kaydedilecek veri yok")
            return False

# ============================================================================
# MAIN
# ============================================================================
def main():
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║   BTC LONG/SHORT MAX PAIN CALCULATOR - DERIBIT                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    calculator = LongShortMaxPainCalculator()
    
    print("⏰ Başlangıç zamanı:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print()
    
    # Sadece bir kez hesapla
    results = calculator.calculate_all_timeframes()
    
    if results:
        print()
        print("💾 Veriler kaydediliyor...")
        print()
        
        # JSON kaydet
        import os
        os.makedirs('data', exist_ok=True)
        
        with open('data/maxpain_longshort.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print("✅ JSON dosyası oluşturuldu: data/maxpain_longshort.json")
        
        # TradingView format
        lines = [
            "# BTC Long/Short Max Pain Levels",
            f"# Updated: {results['update_time']}",
            f"# Current Price: ${results['current_price']:,.2f}",
            "",
            "# Format: TIMEFRAME_LONG=PRICE",
            "#         TIMEFRAME_SHORT=PRICE",
            ""
        ]
        
        for tf, data in results['timeframes'].items():
            lines.append(f"{tf}_LONG={data['long_maxpain']:.0f}")
            lines.append(f"{tf}_SHORT={data['short_maxpain']:.0f}")
        
        with open('data/tradingview_format.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("✅ TradingView dosyası oluşturuldu: data/tradingview_format.txt")
        
        print()
        print("=" * 70)
        print("✅ TÜM İŞLEMLER BAŞARIYLA TAMAMLANDI!")
        print("=" * 70)
        print()
        print("📂 Oluşturulan dosyalar:")
        print("   - data/maxpain_longshort.json")
        print("   - data/tradingview_format.txt")
        print()
        print("🚀 Sırada: GitHub'a yükleme ve TradingView entegrasyonu")
        print("=" * 70)
    else:
        print()
        print("=" * 70)
        print("❌ İŞLEM BAŞARISIZ")
        print("=" * 70)
        print()
        print("Olası nedenler:")
        print("  1. İnternet bağlantısı problemi")
        print("  2. Deribit API geçici olarak erişilemez")
        print("  3. API rate limit aşıldı")
        print()
        print("Çözüm önerileri:")
        print("  - İnternet bağlantınızı kontrol edin")
        print("  - 5-10 dakika sonra tekrar deneyin")
        print("  - VPN kullanıyorsanız kapatmayı deneyin")
        print("=" * 70)

if __name__ == "__main__":
    main()
