import requests
import sys
import json
import time
from datetime import datetime

class CryptoQuizTester:
    def __init__(self, base_url="https://moltbot-setup-d3x8p.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.session_code = None
        self.quiz_id = None
        self.player_id = None
        self.article_data = None

    def log(self, message):
        """Log test messages with timestamps"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test with configurable timeout"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    self.log(f"   Error: {error_data}")
                except:
                    self.log(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            self.log(f"❌ {name} - Request timeout ({timeout}s)")
            return False, {}
        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            return False, {}

    def test_health(self):
        """Test health endpoint and check for BinanceClawQuiz"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        if success and isinstance(response, dict):
            if ('app' in response and response['app'] == 'BinanceClawQuiz') or \
               ('service' in response and response['service'] == 'BinanceClawQuiz'):
                self.log("✅ Health endpoint returns correct app name: BinanceClawQuiz")
                return True
            else:
                self.log(f"❌ Health endpoint doesn't return BinanceClawQuiz, got: {response}")
                return False
        elif success and 'BinanceClawQuiz' in str(response):
            self.log("✅ Health endpoint contains BinanceClawQuiz")
            return True
        else:
            self.log(f"❌ Health endpoint test failed or doesn't contain BinanceClawQuiz")
            return False

    def test_academy_search(self):
        """Test Binance Academy search"""
        success, response = self.run_test(
            "Academy Search",
            "GET", 
            "academy/search?q=bitcoin",
            200,
            timeout=15
        )
        if success and response.get('results'):
            self.log(f"   Found {len(response['results'])} articles")
            # Store first result for later use
            if response['results']:
                self.article_data = response['results'][0]
                return True
        return success

    def test_article_fetch(self):
        """Test article content fetching"""
        if not self.article_data:
            self.log("❌ Skipping article fetch - no article data from search")
            return False
            
        success, response = self.run_test(
            "Article Fetch",
            "POST",
            "academy/article",
            200,
            data={"url": self.article_data['url']},
            timeout=20
        )
        if success:
            self.log(f"   Article: {response.get('title', 'Unknown')}")
            self.log(f"   Content length: {len(response.get('content', ''))}")
            self.article_data.update(response)
        return success

    def test_quiz_generation(self):
        """Test quiz generation from article"""
        # Use short test content to save LLM budget as per requirements
        test_article_data = {
            "url": "https://test.example/article",
            "title": "Bitcoin Fundamentals",
            "content": "Bitcoin is a decentralized digital currency that operates on blockchain technology. Transactions are verified by network nodes through cryptographic algorithms and recorded in a public distributed ledger. Bitcoin enables peer-to-peer transactions without intermediaries like banks. The currency was created in 2009 and uses proof-of-work consensus mechanism."
        }

        success, response = self.run_test(
            "Quiz Generation",
            "POST",
            "quiz/generate",
            200,
            data={
                "article_url": test_article_data["url"],
                "article_title": test_article_data["title"],
                "article_content": test_article_data["content"],
                "num_questions": 3
            },
            timeout=30
        )
        if success:
            self.quiz_id = response.get('quiz_id')
            questions = response.get('questions', [])
            self.log(f"   Quiz ID: {self.quiz_id}")
            self.log(f"   Generated {len(questions)} questions")
        return success

    def test_session_create(self):
        """Test session creation"""
        if not self.quiz_id:
            self.log("❌ Skipping session creation - no quiz ID")
            return False

        success, response = self.run_test(
            "Session Creation",
            "POST",
            "session/create",
            200,
            data={
                "host_name": f"TestHost_{int(time.time())}",
                "quiz_id": self.quiz_id
            }
        )
        if success:
            self.session_code = response.get('code')
            self.log(f"   Session Code: {self.session_code}")
        return success

    def test_session_join(self):
        """Test joining a session"""
        if not self.session_code:
            self.log("❌ Skipping session join - no session code")
            return False

        success, response = self.run_test(
            "Session Join",
            "POST",
            "session/join",
            200,
            data={
                "code": self.session_code,
                "nickname": f"TestPlayer_{int(time.time())}"
            }
        )
        if success:
            self.player_id = response.get('player_id')
            self.log(f"   Player ID: {self.player_id}")
        return success

    def test_session_info(self):
        """Test getting session info"""
        if not self.session_code:
            self.log("❌ Skipping session info - no session code")
            return False

        success, response = self.run_test(
            "Session Info",
            "GET",
            f"session/{self.session_code}",
            200
        )
        if success:
            self.log(f"   Session status: {response.get('status')}")
            self.log(f"   Total questions: {response.get('total_questions')}")
        return success

    def test_session_players(self):
        """Test getting session players"""
        if not self.session_code:
            self.log("❌ Skipping session players - no session code")
            return False

        success, response = self.run_test(
            "Session Players",
            "GET",
            f"session/{self.session_code}/players",
            200
        )
        if success:
            players = response.get('players', [])
            self.log(f"   Players count: {len(players)}")
        return success

    def test_solo_quiz(self):
        """Test solo quiz generation"""
        # Use short test content to save LLM budget as per requirements
        test_article_data = {
            "url": "https://test.example/ethereum",  
            "title": "Ethereum Smart Contracts",
            "content": "Ethereum is a blockchain platform that supports smart contracts. Smart contracts are self-executing programs that automatically enforce agreements. They run on the Ethereum Virtual Machine (EVM) and use Ether (ETH) for transaction fees. Ethereum enables decentralized applications (DApps) and decentralized finance (DeFi) protocols."
        }

        success, response = self.run_test(
            "Solo Quiz Generation",
            "POST",
            "quiz/solo",
            200,
            data={
                "article_url": test_article_data["url"],
                "article_title": test_article_data["title"], 
                "article_content": test_article_data["content"],
                "num_questions": 3
            },
            timeout=30
        )
        if success:
            questions = response.get('questions', [])
            self.log(f"   Solo quiz ID: {response.get('quiz_id')}")
            self.log(f"   Generated {len(questions)} questions with answers")
        return success

    def test_telegram_setup(self):
        """Test Telegram bot setup"""
        success, response = self.run_test(
            "Telegram Setup",
            "POST",
            "telegram/setup",
            200,
            timeout=10
        )
        if success:
            self.log(f"   Commands setup: {response.get('commands', {}).get('ok', False)}")
            self.log(f"   Menu setup: {response.get('menu', {}).get('ok', False)}")
            self.log(f"   Webhook setup: {response.get('webhook', {}).get('ok', False)}")
        return success

def main():
    """Run all backend tests"""
    tester = CryptoQuizTester()
    
    tester.log("🚀 Starting CryptoQuiz Backend Tests")
    tester.log(f"   Base URL: {tester.base_url}")
    
    # Test sequence
    test_results = []
    
    # Basic health check
    test_results.append(("Health Check", tester.test_health()))
    
    # Academy and quiz functionality 
    test_results.append(("Academy Search", tester.test_academy_search()))
    test_results.append(("Article Fetch", tester.test_article_fetch()))
    test_results.append(("Quiz Generation", tester.test_quiz_generation()))
    
    # Session management
    test_results.append(("Session Create", tester.test_session_create()))
    test_results.append(("Session Join", tester.test_session_join()))
    test_results.append(("Session Info", tester.test_session_info()))
    test_results.append(("Session Players", tester.test_session_players()))
    
    # Solo mode
    test_results.append(("Solo Quiz", tester.test_solo_quiz()))
    
    # Telegram integration
    test_results.append(("Telegram Setup", tester.test_telegram_setup()))

    # Print final results
    tester.log("\n" + "="*50)
    tester.log("📊 TEST RESULTS SUMMARY")
    tester.log("="*50)
    
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        tester.log(f"{status} - {test_name}")
    
    tester.log(f"\n📈 Overall: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    tester.log(f"   Success Rate: {success_rate:.1f}%")
    
    # Return exit code
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())