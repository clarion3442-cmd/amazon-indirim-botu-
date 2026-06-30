import requests
from bs4 import BeautifulSoup
import time

# Sizin hazır Telegram bilgileriniz
TELEGRAM_TOKEN = "8546144054:AAGUDXlQSWuKV9rY88njCc9CFGPuG9aL_A0"
CHAT_ID = "1032063964"

# GÜVENLİ LİNKLER: Amazon'un engellemediği kategori vitrin linkleri (/b/ formatı)
HEDEF_URLLER = [
    "https://www.amazon.com.tr/b/?_encoding=UTF8&node=27149247031",  # 1. El Aletleri
    "https://www.amazon.com.tr/b/?_encoding=UTF8&node=12466724031",  # 2. Yapı Market Ana Sayfa
    "https://www.amazon.com.tr/b/?_encoding=UTF8&node=12601898031",  # 3. Bilgisayar ve Bileşenleri
    "https://www.amazon.com.tr/b/?_encoding=UTF8&node=13730623031",  # 4. Akıllı Telefon Aksesuarları
    "https://www.amazon.com.tr/b/?_encoding=UTF8&node=12466532031",  # 5. Ev ve Mutfak Ürünleri
    "https://www.amazon.com.tr/b/?_encoding=UTF8&node=27154563031"   # 6. Bıçaklar ve Hırdavat Ürünleri
]

GONDERILEN_URUNLER = set()

def telegram_mesaj_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram hatası: {e}")

def fiyatı_sayiya_cevir(fiyat_metni):
    if not fiyat_metni:
        return None
    try:
        temiz = fiyat_metni.replace("TL", "").replace("TL\xa0", "").strip()
        temiz = temiz.replace(".", "").replace(",", ".")
        return float(temiz)
    except:
        return None

def amazon_vitrin_tara():
    print(f"🛠️ Toplam {len(HEDEF_URLLER)} farklı Amazon kategorisi taranıyor...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.amazon.com.tr/"
    }
    
    toplam_bulunan = 0

    for sira, url in enumerate(HEDEF_URLLER, 1):
        print(f"👉 {sira}. Kategori taranıyor...")
        try:
            cevap = requests.get(url, headers=headers)
            if cevap.status_code != 200:
                print(f"⚠️ Amazon bu kategoriyi vermedi (Hata Kodu: {cevap.status_code}). Pas geçiliyor.")
                continue
                
            soup = BeautifulSoup(cevap.content, "html.parser")
            urunler = soup.find_all("div", {"data-component-type": "s-search-result"})
            if not urunler:
                urunler = soup.find_all("div", class_="s-result-item")
            
            for urun in urunler:
                try:
                    baslik_etiketi = urun.find("h2")
                    if not baslik_etiketi: continue
                    
                    urun_adi = baslik_etiketi.text.strip()
                    link_etiketi = baslik_etiketi.find("a")
                    if not link_etiketi: continue
                    urun_link = "https://www.amazon.com.tr" + link_etiketi["href"]
                    
                    asin = urun.get("data-asin")
                    if not asin:
                        if "/dp/" in urun_link:
                            asin = urun_link.split("/dp/")[1].split("/")[0]
                        else:
                            asin = urun_adi
                    
                    if asin in GONDERILEN_URUNLER: continue

                    fiyat_kapsayici = urun.find("span", class_="a-price")
                    if not fiyat_kapsayici: continue
                    guncel_fiyat_metni = fiyat_kapsayici.find("span", class_="a-offscreen").text.strip()
                    
                    eski_fiyat_kapsayici = urun.find("span", class_="a-text-price")
                    if not eski_fiyat_kapsayici: continue
                    eski_fiyat_metni = eski_fiyat_kapsayici.find("span", class_="a-offscreen").text.strip()

                    guncel_fiyat = fiyatı_sayiya_cevir(guncel_fiyat_metni)
                    eski_fiyat = fiyatı_sayiya_cevir(eski_fiyat_metni)

                    if guncel_fiyat and eski_fiyat and eski_fiyat > guncel_fiyat:
                        indirim_orani = ((eski_fiyat - guncel_fiyat) / eski_fiyat) * 100
                        
                        # %5 ve üzeri kontrolü
                        if indirim_orani >= 5:
                            toplam_bulunan += 1
                            GONDERILEN_URUNLER.add(asin)
                            
                            mesaj = (
                                f"⚙️ **KATEGORİ İNDİRİMİ YAKALANDI! (% {int(indirim_orani)} İndirim)**\n\n"
                                f"📦 **Ürün:** {urun_adi[:85]}...\n"
                                f"❌ **Eski Fiyat:** {eski_fiyat:,.2f} TL\n"
                                f"✅ **İndirimli Fiyat:** {guncel_fiyat:,.2f} TL\n\n"
                                f"🔗 **Ürün Linki:**\n{urun_link}"
                            )
                            telegram_mesaj_gonder(mesaj)
                            time.sleep(1.5)
                except:
                    continue
            
            # Kategoriler arası geçiş yaparken Amazon'u şüphelendirmemek için kısa bir mola
            time.sleep(2)

        except Exception as e:
            print(f"Kategori taranırken hata oluştu: {e}")
            
    print(f"✅ Tüm tarama bitti. Şartlara uyan {toplam_bulunan} yeni fırsat Telegram'a yollandı.")

if __name__ == "__main__":
    amazon_vitrin_tara()
