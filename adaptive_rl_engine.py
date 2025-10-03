# adaptive_rl_engine.py - Reinforcement Learning Engine for Adaptive Task Policy Learning
import json
import os
import numpy as np
import pickle
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional, Any
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdaptiveRLEngine:
    def __init__(self, feedback_file="user_feedback.json", model_file="rl_model.pkl", 
                 policy_file="task_policies.json", learning_rate=0.1, epsilon=0.1):
        self.feedback_file = feedback_file
        self.model_file = model_file
        self.policy_file = policy_file
        self.learning_rate = learning_rate
        self.epsilon = epsilon  # Exploration rate
        
        # Q-learning components
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.state_action_counts = defaultdict(lambda: defaultdict(int))
        self.recent_interactions = deque(maxlen=1000)
        
        # Policy components
        self.task_policies = {}
        self.intent_success_rates = defaultdict(list)
        self.user_preferences = defaultdict(dict)
        
        # Load existing data
        self.load_feedback_history()
        self.load_model()
        self.load_policies()
        
        # Feature extraction for intent classification
        from sentence_transformers import SentenceTransformer
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    def get_state_features(self, command: str, context: Dict = None) -> str:
        """Extract state features from command and context"""
        features = []
        
        # Command length category
        cmd_len = len(command.split())
        if cmd_len <= 3:
            features.append("short")
        elif cmd_len <= 7:
            features.append("medium")
        else:
            features.append("long")
        
        # Time-based features
        hour = datetime.now().hour
        if 6 <= hour < 12:
            features.append("morning")
        elif 12 <= hour < 18:
            features.append("afternoon")
        elif 18 <= hour < 22:
            features.append("evening")
        else:
            features.append("night")
        
        # Command type indicators
        if any(word in command.lower() for word in ["schedule", "meeting", "event"]):
            features.append("calendar")
        elif any(word in command.lower() for word in ["email", "send", "mail"]):
            features.append("email")
        elif any(word in command.lower() for word in ["search", "find", "google"]):
            features.append("search")
        elif any(word in command.lower() for word in ["open", "run", "launch"]):
            features.append("app")
        
        # Context features
        if context:
            if context.get("has_datetime"):
                features.append("time_specific")
            if context.get("has_recipients"):
                features.append("multi_user")
        
        return "|".join(sorted(features))
    
    def get_enhanced_intent(self, command: str) -> Tuple[str, float]:
        """Get intent prediction enhanced with RL feedback"""
        # Get base intent prediction
        from intent_classifier import predict_intent
        base_intent, base_confidence = predict_intent(command)
        
        # Extract state features
        state = self.get_state_features(command)
        
        # Check if we have learned preferences for this state
        if state in self.q_table:
            # Get Q-values for all possible actions (intents)
            q_values = self.q_table[state]
            
            # Epsilon-greedy action selection
            if np.random.random() < self.epsilon:
                # Explore: choose random intent
                possible_intents = ["calendar_event", "send_email", "web_search", "launch_app", 
                                 "rag_query", "file_manage", "calendar_list", "workflow_trigger"]
                rl_intent = np.random.choice(possible_intents)
                rl_confidence = 0.5
            else:
                # Exploit: choose best intent from Q-table
                if q_values:
                    rl_intent = max(q_values.items(), key=lambda x: x[1])[0]
                    rl_confidence = 0.8
                else:
                    rl_intent = base_intent
                    rl_confidence = base_confidence
        else:
            rl_intent = base_intent
            rl_confidence = base_confidence
        
        # Combine base and RL predictions
        if base_confidence > 0.8:
            # High confidence base prediction
            final_intent = base_intent
            final_confidence = base_confidence
        elif base_confidence < 0.3 and rl_confidence > 0.6:
            # Low confidence base, higher RL confidence
            final_intent = rl_intent
            final_confidence = rl_confidence
        else:
            # Use base prediction as default
            final_intent = base_intent
            final_confidence = base_confidence
        
        logger.info(f"Intent prediction: Base={base_intent}({base_confidence:.2f}), "
                   f"RL={rl_intent}({rl_confidence:.2f}), Final={final_intent}({final_confidence:.2f})")
        
        return final_intent, final_confidence
    
    def log_interaction(self, command: str, intent: str, result: str, user_id: str = "default"):
        """Log interaction for RL training"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "intent": intent,
            "result": result,
            "user_id": user_id,
            "state": self.get_state_features(command),
            "success": None,  # Will be updated when feedback is received
            "feedback_score": None
        }
        
        self.recent_interactions.append(interaction)
        
        # Save to file
        self.save_interaction(interaction)
    
    def record_feedback(self, command_or_id: str, rating: int, user_id: str = "default"):
        """Record user feedback for RL training"""
        if not (1 <= rating <= 5):
            logger.warning(f"Invalid rating: {rating}. Must be 1-5.")
            return
        
        # Find the most recent interaction matching the command
        target_interaction = None
        for interaction in reversed(self.recent_interactions):
            if (interaction["command"] == command_or_id or 
                interaction.get("interaction_id") == command_or_id):
                target_interaction = interaction
                break
        
        if not target_interaction:
            logger.warning(f"No interaction found for: {command_or_id}")
            return
        
        # Update interaction with feedback
        target_interaction["feedback_score"] = rating
        target_interaction["success"] = rating >= 3  # 3+ is considered success
        
        # Update Q-table
        self.update_q_value(target_interaction)
        
        # Update success rates
        intent = target_interaction["intent"]
        self.intent_success_rates[intent].append(rating >= 3)
        
        # Update user preferences
        self.user_preferences[user_id][intent] = self.user_preferences[user_id].get(intent, []) + [rating]
        
        # Save feedback
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": target_interaction["command"],
            "intent": target_interaction["intent"],
            "rating": rating,
            "user_id": user_id,
            "state": target_interaction["state"]
        }
        
        self.save_feedback(feedback_entry)
        
        logger.info(f"Recorded feedback: {rating}/5 for intent '{intent}'")
    
    def update_q_value(self, interaction: Dict):
        """Update Q-value based on interaction feedback"""
        state = interaction["state"]
        action = interaction["intent"]
        reward = self.calculate_reward(interaction)
        
        # Q-learning update
        current_q = self.q_table[state][action]
        
        # Simple Q-update (no next state since this is episodic)
        new_q = current_q + self.learning_rate * (reward - current_q)
        self.q_table[state][action] = new_q
        
        # Update visit count
        self.state_action_counts[state][action] += 1
        
        logger.info(f"Updated Q-value for state '{state}', action '{action}': {current_q:.3f} -> {new_q:.3f}")
    
    def calculate_reward(self, interaction: Dict) -> float:
        """Calculate reward based on interaction outcome"""
        base_reward = 0.0
        
        if interaction.get("feedback_score") is not None:
            # User feedback-based reward
            rating = interaction["feedback_score"]
            base_reward = (rating - 3) / 2.0  # Scale 1-5 to -1 to 1
        
        # Additional reward factors
        intent = interaction["intent"]
        
        # Success rate bonus
        if intent in self.intent_success_rates:
            success_rate = np.mean(self.intent_success_rates[intent][-10:])  # Last 10 attempts
            base_reward += (success_rate - 0.5) * 0.2
        
        # Exploration bonus (encourage trying new state-action pairs)
        state = interaction["state"]
        action = interaction["intent"]
        visit_count = self.state_action_counts[state][action]
        exploration_bonus = 1.0 / (1.0 + visit_count) * 0.1
        
        total_reward = base_reward + exploration_bonus
        return max(-1.0, min(1.0, total_reward))  # Clamp to [-1, 1]
    
    def get_policy_recommendation(self, command: str, user_id: str = "default") -> Dict[str, Any]:
        """Get policy recommendation based on learned preferences"""
        state = self.get_state_features(command)
        
        recommendations = {
            "primary_intent": None,
            "confidence": 0.0,
            "alternative_intents": [],
            "user_preference_factor": 0.0,
            "exploration_factor": self.epsilon
        }
        
        # Get Q-values for this state
        if state in self.q_table:
            q_values = dict(self.q_table[state])
            if q_values:
                # Sort by Q-value
                sorted_intents = sorted(q_values.items(), key=lambda x: x[1], reverse=True)
                recommendations["primary_intent"] = sorted_intents[0][0]
                recommendations["confidence"] = min(1.0, max(0.0, (sorted_intents[0][1] + 1) / 2))
                recommendations["alternative_intents"] = [intent for intent, _ in sorted_intents[1:3]]
        
        # Factor in user preferences
        if user_id in self.user_preferences:
            user_prefs = self.user_preferences[user_id]
            for intent, ratings in user_prefs.items():
                avg_rating = np.mean(ratings)
                if avg_rating > 3.5:
                    recommendations["user_preference_factor"] = (avg_rating - 3) / 2
                    if recommendations["primary_intent"] is None:
                        recommendations["primary_intent"] = intent
                        recommendations["confidence"] = recommendations["user_preference_factor"]
        
        return recommendations
    
    def save_interaction(self, interaction: Dict):
        """Save interaction to file"""
        interactions_file = "interactions.jsonl"
        try:
            with open(interactions_file, "a") as f:
                f.write(json.dumps(interaction) + "\n")
        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")
    
    def save_feedback(self, feedback: Dict):
        """Save feedback to file"""
        try:
            feedbacks = []
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, "r") as f:
                    feedbacks = json.load(f)
            
            feedbacks.append(feedback)
            
            with open(self.feedback_file, "w") as f:
                json.dump(feedbacks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
    
    def load_feedback_history(self):
        """Load historical feedback for training"""
        if not os.path.exists(self.feedback_file):
            return
        
        try:
            with open(self.feedback_file, "r") as f:
                feedbacks = json.load(f)
            
            for feedback in feedbacks:
                intent = feedback["intent"]
                rating = feedback["rating"]
                user_id = feedback.get("user_id", "default")
                
                # Rebuild success rates
                self.intent_success_rates[intent].append(rating >= 3)
                
                # Rebuild user preferences
                if user_id not in self.user_preferences:
                    self.user_preferences[user_id] = {}
                if intent not in self.user_preferences[user_id]:
                    self.user_preferences[user_id][intent] = []
                self.user_preferences[user_id][intent].append(rating)
            
            logger.info(f"Loaded {len(feedbacks)} feedback entries")
            
        except Exception as e:
            logger.error(f"Failed to load feedback history: {e}")
    
    def save_model(self):
        """Save Q-table and model state"""
        model_data = {
            "q_table": dict(self.q_table),
            "state_action_counts": dict(self.state_action_counts),
            "intent_success_rates": dict(self.intent_success_rates),
            "user_preferences": dict(self.user_preferences),
            "learning_rate": self.learning_rate,
            "epsilon": self.epsilon
        }
        
        try:
            with open(self.model_file, "wb") as f:
                pickle.dump(model_data, f)
            logger.info("RL model saved successfully")
        except Exception as e:
            logger.error(f"Failed to save RL model: {e}")
    
    def load_model(self):
        """Load Q-table and model state"""
        if not os.path.exists(self.model_file):
            return
        
        try:
            with open(self.model_file, "rb") as f:
                model_data = pickle.load(f)
            
            # Convert back to defaultdicts
            self.q_table = defaultdict(lambda: defaultdict(float))
            for state, actions in model_data.get("q_table", {}).items():
                for action, value in actions.items():
                    self.q_table[state][action] = value
            
            self.state_action_counts = defaultdict(lambda: defaultdict(int))
            for state, actions in model_data.get("state_action_counts", {}).items():
                for action, count in actions.items():
                    self.state_action_counts[state][action] = count
            
            self.intent_success_rates = defaultdict(list)
            for intent, rates in model_data.get("intent_success_rates", {}).items():
                self.intent_success_rates[intent] = rates
            
            self.user_preferences = defaultdict(dict)
            for user, prefs in model_data.get("user_preferences", {}).items():
                self.user_preferences[user] = prefs
            
            self.learning_rate = model_data.get("learning_rate", self.learning_rate)
            self.epsilon = model_data.get("epsilon", self.epsilon)
            
            logger.info("RL model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load RL model: {e}")
    
    def save_policies(self):
        """Save learned task policies"""
        policies = {}
        
        for state, actions in self.q_table.items():
            if actions:
                best_action = max(actions.items(), key=lambda x: x[1])
                policies[state] = {
                    "best_action": best_action[0],
                    "q_value": best_action[1],
                    "alternatives": sorted(actions.items(), key=lambda x: x[1], reverse=True)[1:3]
                }
        
        try:
            with open(self.policy_file, "w") as f:
                json.dump(policies, f, indent=2)
            logger.info("Task policies saved successfully")
        except Exception as e:
            logger.error(f"Failed to save policies: {e}")
    
    def load_policies(self):
        """Load learned task policies"""
        if not os.path.exists(self.policy_file):
            return
        
        try:
            with open(self.policy_file, "r") as f:
                self.task_policies = json.load(f)
            logger.info("Task policies loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the RL system"""
        metrics = {
            "total_states": len(self.q_table),
            "total_interactions": len(self.recent_interactions),
            "intent_performance": {},
            "learning_stats": {
                "learning_rate": self.learning_rate,
                "exploration_rate": self.epsilon,
                "q_table_size": sum(len(actions) for actions in self.q_table.values())
            }
        }
        
        # Calculate intent-specific metrics
        for intent, rates in self.intent_success_rates.items():
            if rates:
                metrics["intent_performance"][intent] = {
                    "success_rate": np.mean(rates),
                    "total_attempts": len(rates),
                    "recent_success_rate": np.mean(rates[-10:]) if len(rates) >= 10 else np.mean(rates)
                }
        
        return metrics
    
    def decay_exploration(self, decay_rate: float = 0.995, min_epsilon: float = 0.01):
        """Decay exploration rate over time"""
        self.epsilon = max(min_epsilon, self.epsilon * decay_rate)
        logger.info(f"Exploration rate decayed to: {self.epsilon:.4f}")
    
    def __del__(self):
        """Save model when object is destroyed"""
        try:
            self.save_model()
            self.save_policies()
        except:
            pass