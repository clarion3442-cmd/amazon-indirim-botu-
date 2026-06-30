import requests
from bs4 import BeautifulSoup
import time

# Sizin hazır Telegram bilgileriniz
TELEGRAM_TOKEN = "8546144054:AAGUDXlQSWuKV9rY88njCc9CFGPuG9aL_A0"
CHAT_ID = "1032063964"

# Şimdilik sadece 503 hatası vermeyen, erişebildiğimiz 3 ana vitrin linkini bıraktık
HEDEF_URLLER = [
    "https://www.amazon.com.tr/b/?node=13709879031",  # 1. Kulaklık & Aksesuar
    "https://www.amazon.com.tr/b/?node=13709924031",  # 2. Elektronik Grubu
    "https://www.amazon.com.tr/b/?node=13484282031"   # 3. Mutfak Gereçleri
]

GONDERILEN_URUNLER = set()

def telegram_mesaj_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except: pass

def fiyatı_sayiya_cevir(fiyat_metni):
    if not fiyat_metni: return None
    try:
        temiz = fiyat_metni.replace("TL", "").replace("TL\xa0", "").strip()
        temiz = temiz.replace(".", "").replace(",", ".")
        return float(temiz)
    except: return None

def amazon_vitrin_tara():
    print(f"🛠️ Toplam {len(HEDEF_URLLER)} adet güvenli kategori sayfası taranıyor...\n" + "="*50)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.amazon.com.tr/"
    }
    
    toplam_bulunan = 0

    for sira, url in enumerate(HEDEF_URLLER, 1):
        node_id = url.split("node=")[1] if "node=" in url else "Genel"
        print(f"👉 {sira}. Sayfa taranıyor... (Kategori Kodu: {node_id})")
        try:
            cevap = requests.get(url, headers=headers)
            
            if cevap.status_code != 200:
                print(f"   ⚠️ Amazon sayfayı vermedi. Hata Kodu: {cevap.status_code}")
                continue
            
            if "robot" in cevap.text.lower() or "captcha" in cevap.text.lower():
                print("   🚨 Amazon robot kontrolü (Captcha) çıkardı! İçerik okunamıyor.")
                continue
                
            soup = BeautifulSoup(cevap.content, "html.parser")
            
            # YENİ GENİŞ SEÇİCİ: Hem normal arama sonuçlarını hem de vitrin şablonlarını yakalar
            urunler = soup.find_all("div", {"data-component-type": "s-search-result"})
            if not urunler:
                urunler = soup.find_all("div", class_="s-result-item")
            if not urunler:
                urunler = soup.find_all("li", class_="octopus-pc-item") or soup.find_all("div", class_="octopus-pc-item")
            if not urunler:
                urunler = soup.find_all("li", class_="a-carousel-card")

            print(f"   📦 Bilgi: Sayfada {len(urunler)} adet ürün yapısı tespit edildi.")
            
            fiyatli_urun = 0
            indirimli_urun = 0

            for urun in urunler:
                try:
                    # Başlık Bulma
                    baslik_etiketi = urun.find("h2") or urun.find(class_="octopus-pc-asin-title") or urun.find("span", class_="a-truncate-cut")
                    if not baslik_etiketi: continue
                    urun_adi = baslik_etiketi.text.strip()
                    
                    # Link Bulma
                    link_etiketi = urun.find("a")
                    if not link_etiketi: continue
                    urun_link = link_etiketi["href"]
                    if not urun_link.startswith("http"):
                        urun_link = "https://www.amazon.com.tr" + urun_link
                    
                    # Benzersiz ID (ASIN)
                    asin = urun.get("data-asin")
                    if not asin and "/dp/" in urun_link:
                        asin = urun_link.split("/dp/")[1].split("/")[0]
                    if not asin:
                        asin = urun_adi
                    
                    if asin in GONDERILEN_URUNLER: continue

                    # Güncel Fiyat Bulma
                    fiyat_kapsayici = urun.find("span", class_="a-price") or urun.find(class_="octopus-pc-asin-price")
                    if not fiyat_kapsayici: continue
                    
                    offscreen = fiyat_kapsayici.find("span", class_="a-offscreen")
                    guncel_metin = offscreen.text.strip() if offscreen else fiyat_kapsayici.text.strip()
                        
                    # Eski Fiyat Bulma (Üstü çizili fiyat)
                    eski_kapsayici = urun.find("span", class_="a-text-price") or urun.find(class_="octopus-pc-asin-strike-through-price")
                    if not eski_kapsayici: continue
                    
                    eski_offscreen = eski_kapsayici.find("span", class_="a-offscreen")
                    eski_metin = eski_offscreen.text.strip() if eski_offscreen else eski_kapsayici.text.strip()

                    guncel_fiyat = fiyatı_sayiya_cevir(guncel_metin)
                    eski_fiyat = fiyatı_sayiya_cevir(eski_metin)

                    if guncel_fiyat and eski_fiyat:
                        fiyatli_urun += 1
                        if eski_fiyat > guncel_fiyat:
                            indirimli_urun += 1
                            indirim_orani = ((eski_fiyat - guncel_fiyat) / eski_fiyat) * 100
                            
                            if indirim_orani >= 5:
                                toplam_bulunan += 1
                                GONDERILEN_URUNLER.add(asin)
                                
                                mesaj = (
                                    f"🔥 **FIRSAT YAKALANDI! (% {int(indirim_orani)} İndirim)**\n\n"
                                    f"📦 **Ürün:** {urun_adi[:85]}...\n"
                                    f"❌ **Eski Fiyat:** {eski_fiyat:,.2f} TL\n"
                                    f"✅ **İndirimli Fiyat:** {guncel_fiyat:,.2f} TL\n\n"
                                    f"🔗 **Ürün Linki:**\n{urun_link}"
                                )
                                telegram_mesaj_gonder(mesaj)
                                time.sleep(1)
                except:
                    continue
            
            print(f"   💰 Analiz: Fiyatı okunan: {fiyatli_urun} | İndirimi olan: {indirimli_urun}")
            print("-" * 50)
            time.sleep(8)

        except Exception as e:
            print(f"❌ Hata oluştu: {e}")
            
    print(f"\n✅ Tarama bitti. Şartlara uyan {toplam_bulunan} yeni indirim Telegram'a yollandı.")

if __name__ == "__main__":
    amazon_vitrin_tara()
