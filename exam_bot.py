import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import logging
import json
import os

class TelegramExamBot:
    def __init__(self, bot_token, chat_id):
        """
        🤖 Bot Telegram per monitorare esami UNINA
        
        Args:
            bot_token (str): Token del bot Telegram
            chat_id (str): ID della chat dove inviare le notifiche
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.url = "https://esol.unina.it/#esami"
        self.target_exam = "placement test lingua inglese B2 LM ingegneria tutte"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('telegram_exam_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Session per le richieste web
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        })

    def send_telegram_message(self, message, parse_mode='Markdown'):
        """📱 Invia messaggio su Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            if response.json().get('ok'):
                self.logger.info("✅ Messaggio Telegram inviato!")
                return True
            else:
                self.logger.error(f"❌ Errore Telegram API: {response.json()}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Errore invio Telegram: {e}")
            return False

    def send_startup_message(self):
        """🚀 Invia messaggio di avvio"""
        message = f"""
🤖 *Bot UNINA Attivato!*

🎯 *Monitoraggio:* {self.target_exam}
🔗 *Pagina:* [Esami UNINA]({self.url})
⏰ *Avviato:* {datetime.now().strftime('%d/%m/%Y alle %H:%M')}

📡 Il bot controllerà ogni 5 minuti...
💬 Ti avviserò appena l'esame sarà disponibile!

🟢 *Status: ATTIVO*
        """
        return self.send_telegram_message(message)

    def send_exam_found_message(self, exam_text):
        """🎉 Invia messaggio quando trova l'esame"""
        message = f"""
🚨 *ESAME DISPONIBILE!* 🚨

🎯 *TROVATO:* {exam_text}

🔗 *Link diretto:* [VAI ALLA PAGINA ESAMI]({self.url})

⚡ *CORRI A PRENOTARLO!* ⚡

🕒 *Rilevato il:* {datetime.now().strftime('%d/%m/%Y alle %H:%M:%S')}

🤖 _Bot UNINA - Missione compiuta!_
        """
        return self.send_telegram_message(message)

    def send_status_message(self, check_count, found=False):
        """📊 Invia messaggio di stato periodico"""
        if check_count % 12 == 0:  # Ogni ora (12 controlli da 5 min)
            message = f"""
📊 *Aggiornamento Status*

🔍 *Controlli effettuati:* {check_count}
⏰ *Ultimo controllo:* {datetime.now().strftime('%H:%M:%S')}
📋 *Esame cercato:* placement test inglese B2
🟢 *Status:* {'✅ TROVATO!' if found else '🔄 In ricerca...'}

_Il bot continua a monitorare..._
        """
            return self.send_telegram_message(message)
        return True

    def fetch_page(self):
        """🌐 Scarica il contenuto della pagina esami"""
        try:
            self.logger.info(f"🌐 Scaricando pagina: {self.url}")
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"❌ Errore download pagina: {e}")
            return None

    def search_exam_in_content(self, html_content):
        """🔍 Cerca l'esame nel contenuto della pagina"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Rimuovi script e style
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Estrai tutto il testo
            text = soup.get_text().lower()
            
            # Keywords da cercare
            keywords = ['placement', 'test', 'inglese', 'b2', 'ingegneria']
            
            # Verifica se tutti i keywords sono presenti
            keywords_found = {keyword: keyword in text for keyword in keywords}
            
            self.logger.info(f"🔍 Keywords trovate: {keywords_found}")
            
            # Se tutti i keywords sono presenti, cerca la riga specifica
            if all(keywords_found.values()):
                lines = text.split('\n')
                for line in lines:
                    line_clean = line.strip().lower()
                    if all(keyword in line_clean for keyword in keywords):
                        return True, line.strip()
            
            return False, None
            
        except Exception as e:
            self.logger.error(f"❌ Errore nel parsing: {e}")
            return False, None

    def test_telegram_connection(self):
        """🧪 Testa la connessione Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            if response.json().get('ok'):
                bot_info = response.json()['result']
                self.logger.info(f"✅ Bot Telegram connesso: @{bot_info['username']}")
                return True
            else:
                self.logger.error("❌ Token Telegram non valido")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Errore test Telegram: {e}")
            return False

    def monitor(self, check_interval=300, send_status_updates=True):
        """
        🔍 Avvia il monitoraggio continuo
        
        Args:
            check_interval (int): Intervallo controlli in secondi (default: 5 min)
            send_status_updates (bool): Invia aggiornamenti di stato su Telegram
        """
        
        # Test connessione Telegram
        if not self.test_telegram_connection():
            print("❌ Impossibile connettersi a Telegram. Controlla il token!")
            return
        
        # Invia messaggio di avvio
        self.send_startup_message()
        
        self.logger.info("🚀 Monitoraggio avviato!")
        print("🤖 Bot Telegram UNINA attivato!")
        print(f"🎯 Cercando: {self.target_exam}")
        print(f"⏱️ Controllo ogni {check_interval//60} minuti")
        print("💬 Riceverai notifiche su Telegram!")
        print("-" * 50)
        
        check_count = 0
        
        while True:
            try:
                check_count += 1
                current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                
                self.logger.info(f"🔍 Controllo #{check_count} - {current_time}")
                print(f"🔍 Controllo #{check_count} - {current_time}")
                
                # Scarica la pagina
                html_content = self.fetch_page()
                if not html_content:
                    self.logger.warning("⚠️ Pagina non scaricata, riprovo...")
                    time.sleep(30)  # Aspetta meno tempo se c'è un errore
                    continue
                
                # Cerca l'esame
                found, exam_text = self.search_exam_in_content(html_content)
                
                if found:
                    # 🎉 ESAME TROVATO!
                    self.logger.info(f"🎉 ESAME TROVATO: {exam_text}")
                    print(f"\n{'='*60}")
                    print("🎯 ESAME DISPONIBILE!")
                    print(f"📚 Trovato: {exam_text}")
                    print(f"🔗 Link: {self.url}")
                    print(f"{'='*60}")
                    
                    # Invia notifica Telegram
                    if self.send_exam_found_message(exam_text or self.target_exam):
                        print("✅ Notifica Telegram inviata!")
                    
                    print("\n🎉 MISSIONE COMPIUTA! Vai a prenotare l'esame!")
                    break
                
                else:
                    self.logger.info("❌ Esame non ancora disponibile")
                    print("❌ Esame non trovato, continuo a cercare...")
                
                # Invia aggiornamenti di stato periodici
                if send_status_updates:
                    self.send_status_message(check_count, found)
                
                # Aspetta prima del prossimo controllo
                print(f"⏳ Prossimo controllo tra {check_interval//60} minuti...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("⏹️ Monitoraggio interrotto dall'utente")
                stop_message = """
⏹️ *Bot Fermato*

Il monitoraggio è stato interrotto.
Grazie per aver usato il Bot UNINA! 🤖
                """
                self.send_telegram_message(stop_message)
                print("\n👋 Bot fermato dall'utente!")
                break
                
            except Exception as e:
                self.logger.error(f"💥 Errore inaspettato: {e}")
                print(f"💥 Errore: {e}")
                time.sleep(60)  # Aspetta 1 minuto prima di riprovare

def main():
    """🎯 Configurazione e avvio del bot da variabili d'ambiente"""
    
    print("🤖 Bot Telegram per Esami UNINA")
    print("=" * 40)
    
    # Ottieni token e chat_id da variabili ambiente (Railway)
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    CHAT_ID = os.environ.get("CHAT_ID")
    
    # Verifica configurazione
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ ERRORE: BOT_TOKEN o CHAT_ID non sono definiti nelle variabili d'ambiente!")
        print("\n✅ Assicurati di averle impostate correttamente su Railway.")
        return
    
    # Crea e avvia il bot
    bot = TelegramExamBot(BOT_TOKEN, CHAT_ID)
    
    # Avvia monitoraggio (controllo ogni 5 minuti)
    bot.monitor(check_interval=300, send_status_updates=True)

if __name__ == "__main__":
    main()
