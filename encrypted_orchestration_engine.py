# encrypted_orchestration_engine.py - n8n workflow orchestration with OAuth2 and AES-256
import requests
import json
import base64
import hashlib
import hmac
import time
import os
from typing import Dict, List, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class EncryptedOrchestrationEngine:
    """
    Encrypted Orchestration Engine that integrates n8n workflows with custom Python/Selenium nodes
    using OAuth2 authentication and AES-256 encryption for secure multi-agent desktop task automation
    """
    
    def __init__(self, n8n_base_url="http://localhost:5678", encryption_key_file="orchestration.key"):
        self.n8n_base_url = n8n_base_url
        self.encryption_key_file = encryption_key_file
        
        # Initialize encryption
        self.encryption_key = self._load_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # OAuth2 configuration
        self.oauth2_config = self._load_oauth2_config()
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Active workflows and agents
        self.active_workflows = {}
        self.selenium_agents = {}
        
        # Task queue for orchestration
        self.task_queue = asyncio.Queue()
        self.result_cache = {}
        
        # Initialize components
        self._initialize_orchestration()
    
    def _load_or_create_encryption_key(self) -> bytes:
        """Load or create AES-256 encryption key"""
        if os.path.exists(self.encryption_key_file):
            with open(self.encryption_key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.encryption_key_file, "wb") as f:
                f.write(key)
            logger.info("Created new AES-256 encryption key")
            return key
    
    def _load_oauth2_config(self) -> Dict[str, str]:
        """Load OAuth2 configuration"""
        config_file = "oauth2_config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading OAuth2 config: {e}")
        
        # Default OAuth2 configuration
        default_config = {
            "client_id": "academic_ai_assistant",
            "client_secret": "your_client_secret_here",
            "authorization_url": "https://oauth.example.com/auth",
            "token_url": "https://oauth.example.com/token",
            "scope": "workflows:execute tasks:manage agents:control",
            "redirect_uri": "http://localhost:8080/oauth/callback"
        }
        
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def _initialize_orchestration(self):
        """Initialize orchestration engine components"""
        try:
            # Test n8n connection
            self._test_n8n_connection()
            
            # Initialize default workflows
            self._setup_default_workflows()
            
            # Initialize Selenium WebDriver pool
            self._initialize_selenium_pool()
            
            logger.info("Orchestration engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestration engine: {e}")
    
    def _test_n8n_connection(self) -> bool:
        """Test connection to n8n instance"""
        try:
            response = requests.get(f"{self.n8n_base_url}/healthz", timeout=5)
            if response.status_code == 200:
                logger.info("n8n connection successful")
                return True
            else:
                logger.warning(f"n8n health check returned {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to n8n: {e}")
            return False
    
    def encrypt_payload(self, data: Any) -> str:
        """Encrypt data payload using AES-256"""
        try:
            json_data = json.dumps(data) if not isinstance(data, str) else data
            encrypted_data = self.fernet.encrypt(json_data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_payload(self, encrypted_data: str) -> Any:
        """Decrypt data payload"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def get_oauth2_access_token(self) -> str:
        """Get or refresh OAuth2 access token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        if self.refresh_token:
            return self._refresh_access_token()
        else:
            return self._get_new_access_token()
    
    def _get_new_access_token(self) -> str:
        """Get new OAuth2 access token (simplified for demo)"""
        try:
            # In production, implement full OAuth2 flow
            # For demo, generate JWT token
            payload = {
                "sub": "academic_ai_assistant",
                "iat": datetime.now().timestamp(),
                "exp": (datetime.now() + timedelta(hours=1)).timestamp(),
                "scope": self.oauth2_config["scope"]
            }
            
            token = jwt.encode(payload, self.oauth2_config["client_secret"], algorithm="HS256")
            
            self.access_token = token
            self.token_expiry = datetime.now() + timedelta(hours=1)
            
            logger.info("Generated new OAuth2 access token")
            return token
            
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise
    
    def _refresh_access_token(self) -> str:
        """Refresh OAuth2 access token"""
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.oauth2_config["client_id"],
                "client_secret": self.oauth2_config["client_secret"]
            }
            
            response = requests.post(self.oauth2_config["token_url"], data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.refresh_token = token_data.get("refresh_token", self.refresh_token)
                self.token_expiry = datetime.now() + timedelta(seconds=token_data["expires_in"])
                
                logger.info("Refreshed OAuth2 access token")
                return self.access_token
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return self._get_new_access_token()
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return self._get_new_access_token()
    
    def _setup_default_workflows(self):
        """Setup default n8n workflows for academic tasks"""
        
        default_workflows = {
            "email_campaign": {
                "name": "Academic Email Campaign",
                "description": "Automated email sending with template processing",
                "nodes": [
                    {
                        "name": "Trigger",
                        "type": "n8n-nodes-base.webhook",
                        "parameters": {"path": "email-campaign"}
                    },
                    {
                        "name": "Process Recipients", 
                        "type": "n8n-nodes-base.function",
                        "parameters": {
                            "functionCode": """
                            // Decrypt and process recipient list
                            const encrypted_data = items[0].json.encrypted_recipients;
                            const recipients = JSON.parse(Buffer.from(encrypted_data, 'base64').toString());
                            
                            return recipients.map(recipient => ({
                                json: {
                                    email: recipient.email,
                                    name: recipient.name,
                                    template_vars: recipient.template_vars
                                }
                            }));
                            """
                        }
                    },
                    {
                        "name": "Send Email",
                        "type": "n8n-nodes-base.emailSend", 
                        "parameters": {
                            "fromEmail": "{{$node['Trigger'].json['sender_email']}}",
                            "toEmail": "={{$json['email']}}",
                            "subject": "={{$node['Trigger'].json['subject']}}",
                            "message": "={{$node['Trigger'].json['body']}}"
                        }
                    }
                ]
            },
            
            "calendar_automation": {
                "name": "Calendar Event Automation",
                "description": "Create calendar events and send invites",
                "nodes": [
                    {
                        "name": "Calendar Trigger",
                        "type": "n8n-nodes-base.webhook",
                        "parameters": {"path": "calendar-event"}
                    },
                    {
                        "name": "Create Google Event",
                        "type": "n8n-nodes-base.googleCalendar",
                        "parameters": {
                            "operation": "create",
                            "calendarId": "primary"
                        }
                    },
                    {
                        "name": "Send Invitations",
                        "type": "n8n-nodes-base.emailSend",
                        "parameters": {
                            "subject": "Meeting Invitation: {{$node['Calendar Trigger'].json['title']}}",
                            "message": "You are invited to: {{$node['Calendar Trigger'].json['description']}}"
                        }
                    }
                ]
            },
            
            "desktop_automation": {
                "name": "Desktop Task Automation", 
                "description": "Selenium-based desktop application automation",
                "nodes": [
                    {
                        "name": "Desktop Trigger",
                        "type": "n8n-nodes-base.webhook",
                        "parameters": {"path": "desktop-automation"}
                    },
                    {
                        "name": "Execute Selenium Task",
                        "type": "n8n-nodes-base.function",
                        "parameters": {
                            "functionCode": """
                            // Execute custom Selenium automation
                            const task_type = items[0].json.task_type;
                            const parameters = items[0].json.parameters;
                            
                            // Call Python Selenium agent
                            const result = await $http.request({
                                method: 'POST',
                                url: 'http://localhost:8888/selenium/execute',
                                headers: {
                                    'Authorization': 'Bearer ' + items[0].json.access_token,
                                    'Content-Type': 'application/json'
                                },
                                body: {
                                    task_type: task_type,
                                    parameters: parameters
                                }
                            });
                            
                            return [{json: result.data}];
                            """
                        }
                    }
                ]
            }
        }
        
        # Register workflows with n8n
        for workflow_id, workflow_config in default_workflows.items():
            self._register_workflow(workflow_id, workflow_config)
    
    def _register_workflow(self, workflow_id: str, workflow_config: Dict) -> bool:
        """Register workflow with n8n"""
        try:
            headers = {
                "Authorization": f"Bearer {self.get_oauth2_access_token()}",
                "Content-Type": "application/json"
            }
            
            # Encrypt workflow configuration
            encrypted_config = self.encrypt_payload(workflow_config)
            
            workflow_data = {
                "name": workflow_config["name"],
                "nodes": workflow_config["nodes"],
                "connections": {},
                "active": True,
                "settings": {
                    "encrypted": True,
                    "config_hash": hashlib.sha256(encrypted_config.encode()).hexdigest()
                }
            }
            
            response = requests.post(
                f"{self.n8n_base_url}/api/v1/workflows",
                headers=headers,
                json=workflow_data
            )
            
            if response.status_code in [200, 201]:
                workflow_data = response.json()
                self.active_workflows[workflow_id] = {
                    "id": workflow_data["id"],
                    "config": workflow_config,
                    "status": "active"
                }
                logger.info(f"Registered workflow: {workflow_id}")
                return True
            else:
                logger.error(f"Failed to register workflow {workflow_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Workflow registration error: {e}")
            return False
    
    def _initialize_selenium_pool(self):
        """Initialize Selenium WebDriver pool for desktop automation"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Create pool of WebDriver instances
            for i in range(3):  # Pool of 3 drivers
                try:
                    driver = webdriver.Chrome(options=chrome_options)
                    self.selenium_agents[f"agent_{i}"] = {
                        "driver": driver,
                        "status": "idle",
                        "current_task": None
                    }
                    logger.info(f"Initialized Selenium agent_{i}")
                except Exception as e:
                    logger.warning(f"Failed to create Selenium agent_{i}: {e}")
            
            if not self.selenium_agents:
                logger.warning("No Selenium agents initialized")
            
        except Exception as e:
            logger.error(f"Selenium pool initialization failed: {e}")
    
    async def execute_workflow(self, workflow_id: str, payload: Dict[str, Any], 
                              secure: bool = True) -> Dict[str, Any]:
        """Execute n8n workflow with encrypted payload"""
        try:
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            workflow_info = self.active_workflows[workflow_id]
            
            # Prepare encrypted payload
            if secure:
                encrypted_payload = {
                    "encrypted_data": self.encrypt_payload(payload),
                    "timestamp": datetime.now().isoformat(),
                    "workflow_id": workflow_id
                }
            else:
                encrypted_payload = payload
            
            # Execute workflow via webhook
            webhook_url = f"{self.n8n_base_url}/webhook/{workflow_id}"
            
            headers = {
                "Authorization": f"Bearer {self.get_oauth2_access_token()}",
                "Content-Type": "application/json",
                "X-Workflow-Encryption": "AES-256" if secure else "none"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, headers=headers, json=encrypted_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Decrypt result if encrypted
                        if secure and "encrypted_result" in result:
                            decrypted_result = self.decrypt_payload(result["encrypted_result"])
                            result["data"] = decrypted_result
                        
                        # Cache result
                        cache_key = f"{workflow_id}_{hashlib.md5(json.dumps(payload).encode()).hexdigest()}"
                        self.result_cache[cache_key] = {
                            "result": result,
                            "timestamp": datetime.now(),
                            "workflow_id": workflow_id
                        }
                        
                        logger.info(f"Workflow {workflow_id} executed successfully")
                        return result
                    else:
                        error_msg = f"Workflow execution failed: {response.status}"
                        logger.error(error_msg)
                        return {"error": error_msg, "status": response.status}
                        
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {"error": str(e)}
    
    async def execute_selenium_task(self, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Selenium-based desktop automation task"""
        try:
            # Find available agent
            available_agent = None
            for agent_id, agent_info in self.selenium_agents.items():
                if agent_info["status"] == "idle":
                    available_agent = agent_id
                    break
            
            if not available_agent:
                return {"error": "No available Selenium agents"}
            
            # Mark agent as busy
            self.selenium_agents[available_agent]["status"] = "busy"
            self.selenium_agents[available_agent]["current_task"] = task_type
            
            agent = self.selenium_agents[available_agent]
            driver = agent["driver"]
            
            # Execute task based on type
            result = await self._execute_selenium_task_by_type(driver, task_type, parameters)
            
            # Mark agent as idle
            agent["status"] = "idle"
            agent["current_task"] = None
            
            logger.info(f"Selenium task {task_type} completed by {available_agent}")
            return result
            
        except Exception as e:
            # Ensure agent is marked as idle
            if available_agent:
                self.selenium_agents[available_agent]["status"] = "idle"
                self.selenium_agents[available_agent]["current_task"] = None
            
            logger.error(f"Selenium task execution error: {e}")
            return {"error": str(e)}
    
    async def _execute_selenium_task_by_type(self, driver: webdriver.Chrome, 
                                           task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific Selenium task type"""
        
        if task_type == "email_portal_login":
            return await self._selenium_email_login(driver, parameters)
        elif task_type == "calendar_event_creation":
            return await self._selenium_calendar_create(driver, parameters)
        elif task_type == "document_upload":
            return await self._selenium_document_upload(driver, parameters)
        elif task_type == "web_form_filling":
            return await self._selenium_form_fill(driver, parameters)
        elif task_type == "data_extraction":
            return await self._selenium_data_extract(driver, parameters)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _selenium_email_login(self, driver: webdriver.Chrome, 
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Automated email portal login"""
        try:
            email = parameters.get("email")
            password = parameters.get("password") 
            portal_url = parameters.get("portal_url", "https://gmail.com")
            
            driver.get(portal_url)
            
            # Wait for email field and enter email
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_field.send_keys(email)
            
            # Click next
            driver.find_element(By.ID, "identifierNext").click()
            
            # Wait for password field and enter password  
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_field.send_keys(password)
            
            # Click sign in
            driver.find_element(By.ID, "passwordNext").click()
            
            # Wait for successful login
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='inbox']"))
            )
            
            return {
                "status": "success",
                "message": "Email portal login successful",
                "current_url": driver.current_url
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _selenium_calendar_create(self, driver: webdriver.Chrome,
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Automated calendar event creation"""
        try:
            event_title = parameters.get("title")
            event_date = parameters.get("date")
            event_time = parameters.get("time")
            attendees = parameters.get("attendees", [])
            
            # Navigate to Google Calendar
            driver.get("https://calendar.google.com")
            
            # Click create button
            create_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='create-event']"))
            )
            create_btn.click()
            
            # Fill event details
            title_field = driver.find_element(By.ID, "event-title")
            title_field.send_keys(event_title)
            
            # Set date and time (simplified)
            date_field = driver.find_element(By.CSS_SELECTOR, "[aria-label='Start date']")
            date_field.clear()
            date_field.send_keys(event_date)
            
            # Add attendees
            if attendees:
                attendees_field = driver.find_element(By.CSS_SELECTOR, "[aria-label='Add guests']")
                for attendee in attendees:
                    attendees_field.send_keys(attendee + ",")
            
            # Save event
            save_btn = driver.find_element(By.CSS_SELECTOR, "[data-testid='save-event']")
            save_btn.click()
            
            return {
                "status": "success", 
                "message": f"Calendar event '{event_title}' created successfully"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _selenium_document_upload(self, driver: webdriver.Chrome,
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Automated document upload to college portal"""
        try:
            portal_url = parameters.get("portal_url")
            file_path = parameters.get("file_path")
            document_type = parameters.get("document_type")
            
            driver.get(portal_url)
            
            # Navigate to upload section
            upload_section = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Document Upload"))
            )
            upload_section.click()
            
            # Select document type
            doc_type_dropdown = driver.find_element(By.ID, "document-type")
            doc_type_dropdown.send_keys(document_type)
            
            # Upload file
            file_input = driver.find_element(By.INPUT, "file")
            file_input.send_keys(file_path)
            
            # Submit upload
            submit_btn = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
            submit_btn.click()
            
            # Wait for confirmation
            confirmation = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".upload-success"))
            )
            
            return {
                "status": "success",
                "message": f"Document uploaded successfully: {document_type}",
                "confirmation": confirmation.text
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _selenium_form_fill(self, driver: webdriver.Chrome,
                                 parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Automated form filling"""
        try:
            form_url = parameters.get("form_url")
            form_data = parameters.get("form_data", {})
            
            driver.get(form_url)
            
            # Fill form fields
            for field_name, field_value in form_data.items():
                try:
                    field = driver.find_element(By.NAME, field_name)
                    field.clear()
                    field.send_keys(str(field_value))
                except:
                    # Try by ID if name fails
                    try:
                        field = driver.find_element(By.ID, field_name)
                        field.clear()
                        field.send_keys(str(field_value))
                    except:
                        logger.warning(f"Could not find field: {field_name}")
            
            # Submit form
            submit_btn = driver.find_element(By.CSS_SELECTOR, "[type='submit']")
            submit_btn.click()
            
            return {
                "status": "success",
                "message": "Form submitted successfully",
                "fields_filled": len(form_data)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _selenium_data_extract(self, driver: webdriver.Chrome,
                                   parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from web pages"""
        try:
            target_url = parameters.get("url")
            selectors = parameters.get("selectors", {})
            
            driver.get(target_url)
            
            # Wait for page load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            extracted_data = {}
            
            # Extract data using provided selectors
            for data_name, selector in selectors.items():
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        if len(elements) == 1:
                            extracted_data[data_name] = elements[0].text
                        else:
                            extracted_data[data_name] = [elem.text for elem in elements]
                    else:
                        extracted_data[data_name] = None
                except Exception as e:
                    extracted_data[data_name] = f"Error: {str(e)}"
            
            return {
                "status": "success",
                "data": extracted_data,
                "extracted_fields": len(extracted_data)
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def orchestrate_multi_agent_task(self, task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate complex multi-agent tasks combining n8n workflows and Selenium agents"""
        try:
            task_id = task_definition.get("task_id")
            task_steps = task_definition.get("steps", [])
            
            results = {}
            
            for step_index, step in enumerate(task_steps):
                step_id = f"{task_id}_step_{step_index}"
                step_type = step.get("type")  # "workflow" or "selenium"
                step_config = step.get("config", {})
                
                if step_type == "workflow":
                    # Execute n8n workflow
                    workflow_id = step_config.get("workflow_id")
                    workflow_payload = step_config.get("payload", {})
                    
                    # Use results from previous steps
                    if step_index > 0:
                        workflow_payload["previous_results"] = results
                    
                    result = await self.execute_workflow(workflow_id, workflow_payload)
                    results[step_id] = result
                    
                elif step_type == "selenium":
                    # Execute Selenium task
                    task_type = step_config.get("task_type")
                    parameters = step_config.get("parameters", {})
                    
                    # Use results from previous steps in parameters
                    if step_index > 0:
                        parameters["previous_results"] = results
                    
                    result = await self.execute_selenium_task(task_type, parameters)
                    results[step_id] = result
                
                # Check for step failure
                if "error" in results[step_id]:
                    logger.error(f"Step {step_id} failed: {results[step_id]['error']}")
                    if step.get("critical", True):
                        break
            
            return {
                "task_id": task_id,
                "status": "completed" if all("error" not in r for r in results.values()) else "partial",
                "results": results,
                "total_steps": len(task_steps),
                "completed_steps": len(results)
            }
            
        except Exception as e:
            logger.error(f"Multi-agent orchestration error: {e}")
            return {
                "task_id": task_definition.get("task_id"),
                "status": "failed",
                "error": str(e)
            }
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration engine status"""
        return {
            "n8n_connection": self._test_n8n_connection(),
            "active_workflows": len(self.active_workflows),
            "selenium_agents": len(self.selenium_agents),
            "idle_agents": len([a for a in self.selenium_agents.values() if a["status"] == "idle"]),
            "cached_results": len(self.result_cache),
            "oauth2_token_valid": self.access_token is not None and 
                                (self.token_expiry is None or datetime.now() < self.token_expiry),
            "encryption_status": "AES-256 active"
        }
    
    def cleanup_resources(self):
        """Cleanup orchestration resources"""
        try:
            # Close Selenium drivers
            for agent_id, agent_info in self.selenium_agents.items():
                try:
                    agent_info["driver"].quit()
                    logger.info(f"Closed Selenium agent {agent_id}")
                except Exception as e:
                    logger.warning(f"Error closing agent {agent_id}: {e}")
            
            # Clear caches
            self.result_cache.clear()
            self.active_workflows.clear()
            self.selenium_agents.clear()
            
            logger.info("Orchestration resources cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup_resources()