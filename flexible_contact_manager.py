# flexible_contact_manager.py - CSV-based contact management for easy customization
import pandas as pd
import os
import json
import re
from typing import List, Dict, Optional, Set, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FlexibleContactManager:
    """CSV-based contact manager for easy lecturer customization"""
    
    def __init__(self, base_path="data"):
        self.base_path = Path(base_path)
        self.contacts_path = self.base_path / "contacts"
        self.config_path = self.base_path / "config"
        
        # Initialize directory structure
        self.contacts_path.mkdir(parents=True, exist_ok=True)
        
        # DataFrames for different contact types
        self.master_df = None
        self.students_dfs = {}  # By batch year
        self.faculty_dfs = {}   # By department
        self.staff_df = None
        
        # Load configuration
        self.permissions_config = self.load_permissions_config()
        
        # Load all contact files
        self.load_all_contacts()
        
        # Initialize with sample data if empty
        if self.is_database_empty():
            self.initialize_sample_data()
    
    def load_permissions_config(self) -> Dict:
        """Load email permissions configuration"""
        permissions_file = self.config_path / "permissions.json"
        
        if permissions_file.exists():
            try:
                with open(permissions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading permissions: {e}")
        
        # Default permissions
        default_permissions = {
            "role_hierarchy": {
                "Principal": {"level": 10, "can_email": ["everyone"]},
                "Dean": {"level": 9, "can_email": ["faculty", "staff", "students"]},
                "HOD": {"level": 8, "can_email": ["department_faculty", "department_students", "staff"]},
                "Professor": {"level": 7, "can_email": ["students", "faculty", "staff"]},
                "Associate Professor": {"level": 6, "can_email": ["students", "faculty"]},
                "Assistant Professor": {"level": 5, "can_email": ["students", "same_dept_faculty"]},
                "Lab Assistant": {"level": 3, "can_email": ["students"]},
                "Admin Staff": {"level": 4, "can_email": ["faculty", "staff"]}
            },
            "email_limits": {
                "Professor": {"daily_limit": 500, "bulk_limit": 100},
                "Associate Professor": {"daily_limit": 300, "bulk_limit": 75},
                "Assistant Professor": {"daily_limit": 200, "bulk_limit": 50},
                "HOD": {"daily_limit": 1000, "bulk_limit": 200}
            },
            "approval_required": {
                "external_emails": ["Assistant Professor", "Lab Assistant"],
                "cross_department": ["Assistant Professor"],
                "all_students": ["Assistant Professor"]
            }
        }
        
        # Save default permissions
        self.config_path.mkdir(parents=True, exist_ok=True)
        with open(permissions_file, 'w', encoding='utf-8') as f:
            json.dump(default_permissions, f, indent=2)
        
        return default_permissions
    
    def load_all_contacts(self):
        """Load all contact files"""
        try:
            # Load master contacts file
            master_file = self.contacts_path / "contacts_master.csv"
            if master_file.exists():
                self.master_df = pd.read_csv(master_file)
                logger.info(f"Loaded {len(self.master_df)} contacts from master file")
            
            # Load student batch files
            for batch_file in self.contacts_path.glob("students_*.csv"):
                batch_year = batch_file.stem.replace("students_", "")
                try:
                    self.students_dfs[batch_year] = pd.read_csv(batch_file)
                    logger.info(f"Loaded {len(self.students_dfs[batch_year])} students from {batch_year} batch")
                except Exception as e:
                    logger.error(f"Error loading {batch_file}: {e}")
            
            # Load faculty department files  
            for faculty_file in self.contacts_path.glob("faculty_*.csv"):
                dept_code = faculty_file.stem.replace("faculty_", "")
                try:
                    self.faculty_dfs[dept_code] = pd.read_csv(faculty_file)
                    logger.info(f"Loaded {len(self.faculty_dfs[dept_code])} faculty from {dept_code} department")
                except Exception as e:
                    logger.error(f"Error loading {faculty_file}: {e}")
            
            # Load staff file
            staff_file = self.contacts_path / "staff_admin.csv"
            if staff_file.exists():
                self.staff_df = pd.read_csv(staff_file)
                logger.info(f"Loaded {len(self.staff_df)} staff members")
        
        except Exception as e:
            logger.error(f"Error loading contacts: {e}")
    
    def is_database_empty(self) -> bool:
        """Check if contact database is empty"""
        return (self.master_df is None or len(self.master_df) == 0) and \
               len(self.students_dfs) == 0 and len(self.faculty_dfs) == 0
    
    def initialize_sample_data(self):
        """Initialize with sample academic data"""
        logger.info("Initializing sample contact data...")
        
        # Sample master contacts
        sample_master = [
            {
                'name': 'Dr. Rajesh Kumar', 'email': 'rajesh.kumar@sjec.ac.in', 'role': 'faculty',
                'department': 'Computer Science', 'designation': 'Professor', 'employee_id': 'FAC001',
                'specialization': 'Machine Learning', 'year_joined': '2010', 'status': 'active'
            },
            {
                'name': 'Dr. Priya Sharma', 'email': 'priya.sharma@sjec.ac.in', 'role': 'faculty', 
                'department': 'Computer Science', 'designation': 'Associate Professor', 'employee_id': 'FAC002',
                'specialization': 'Data Science', 'year_joined': '2015', 'status': 'active'
            },
            {
                'name': 'Dr. Arjun Nair', 'email': 'arjun.nair@sjec.ac.in', 'role': 'staff',
                'department': 'Computer Science', 'designation': 'HOD', 'employee_id': 'HOD001',
                'specialization': 'Computer Networks', 'year_joined': '2008', 'status': 'active'
            }
        ]
        
        # Sample students data
        sample_students_2024 = [
            {
                'name': 'Arun Kumar', 'email': 'arun.2024cse001@sjec.ac.in', 'student_id': '2024CSE001',
                'department': 'Computer Science', 'batch': '2024', 'semester': '1', 'section': 'A',
                'phone': '9876543210', 'status': 'active'
            },
            {
                'name': 'Sneha Patel', 'email': 'sneha.2024cse002@sjec.ac.in', 'student_id': '2024CSE002', 
                'department': 'Computer Science', 'batch': '2024', 'semester': '1', 'section': 'A',
                'phone': '9876543211', 'status': 'active'
            },
            {
                'name': 'Vikram Singh', 'email': 'vikram.2024cse003@sjec.ac.in', 'student_id': '2024CSE003',
                'department': 'Computer Science', 'batch': '2024', 'semester': '1', 'section': 'B', 
                'phone': '9876543212', 'status': 'active'
            }
        ]
        
        # Sample faculty data
        sample_faculty_cse = [
            {
                'name': 'Dr. Rajesh Kumar', 'email': 'rajesh.kumar@sjec.ac.in', 'employee_id': 'FAC001',
                'designation': 'Professor', 'specialization': 'Machine Learning', 
                'subjects_taught': 'ML,AI,Python', 'cabin_no': 'C-101', 'phone': '9876543210',
                'years_experience': '14', 'qualification': 'PhD Computer Science'
            },
            {
                'name': 'Dr. Priya Sharma', 'email': 'priya.sharma@sjec.ac.in', 'employee_id': 'FAC002',
                'designation': 'Associate Professor', 'specialization': 'Data Science',
                'subjects_taught': 'DS,Statistics,R', 'cabin_no': 'C-102', 'phone': '9876543211', 
                'years_experience': '9', 'qualification': 'PhD Statistics'
            }
        ]
        
        # Create and save sample files
        self.create_sample_files(sample_master, sample_students_2024, sample_faculty_cse)
        
        # Reload contacts
        self.load_all_contacts()
        
        logger.info("Sample data initialized successfully")
    
    def create_sample_files(self, master_data, students_data, faculty_data):
        """Create sample CSV files"""
        
        # Master contacts file
        master_df = pd.DataFrame(master_data)
        master_df.to_csv(self.contacts_path / "contacts_master.csv", index=False)
        
        # Students batch file  
        students_df = pd.DataFrame(students_data)
        students_df.to_csv(self.contacts_path / "students_2024.csv", index=False)
        
        # Faculty department file
        faculty_df = pd.DataFrame(faculty_data) 
        faculty_df.to_csv(self.contacts_path / "faculty_cse.csv", index=False)
        
        # Staff file (empty initially)
        staff_columns = ['name', 'email', 'employee_id', 'designation', 'department', 'phone', 'status']
        staff_df = pd.DataFrame(columns=staff_columns)
        staff_df.to_csv(self.contacts_path / "staff_admin.csv", index=False)
    
    def smart_recipient_extraction(self, command: str) -> List[str]:
        """Extract recipients from natural language commands"""
        recipients = []
        command_lower = command.lower()
        
        # Department-wide patterns
        dept_patterns = {
            r'\ball\s+cse|entire\s+cse|cse\s+department|computer\s+science': 'Computer Science',
            r'\ball\s+ece|entire\s+ece|ece\s+department|electronics': 'Electronics', 
            r'\ball\s+mech|entire\s+mech|mech\s+department|mechanical': 'Mechanical',
            r'\ball\s+civil|entire\s+civil|civil\s+department': 'Civil'
        }
        
        for pattern, dept_name in dept_patterns.items():
            if re.search(pattern, command_lower):
                recipients.extend(self.get_department_emails(dept_name))
        
        # Role-based patterns
        role_patterns = {
            r'\ball\s+students|entire\s+student\s+body': lambda: self.get_all_students(),
            r'\ball\s+faculty|entire\s+faculty|faculty\s+members': lambda: self.get_all_faculty(),
            r'\ball\s+staff|admin\s+staff|support\s+staff': lambda: self.get_all_staff(),
            r'\ball\s+professors|senior\s+faculty': lambda: self.get_faculty_by_designation(['Professor']),
            r'associate\s+professors': lambda: self.get_faculty_by_designation(['Associate Professor']),
            r'assistant\s+professors': lambda: self.get_faculty_by_designation(['Assistant Professor']),
            r'hods|heads\s+of\s+department': lambda: self.get_faculty_by_designation(['HOD'])
        }
        
        for pattern, func in role_patterns.items():
            if re.search(pattern, command_lower):
                recipients.extend(func())
        
        # Batch-specific patterns
        batch_patterns = {
            r'2024\s+batch|first\s+year|fresher|1st\s+year': '2024',
            r'2023\s+batch|second\s+year|2nd\s+year': '2023', 
            r'2022\s+batch|third\s+year|3rd\s+year': '2022',
            r'2021\s+batch|final\s+year|fourth\s+year|4th\s+year': '2021'
        }
        
        for pattern, batch in batch_patterns.items():
            if re.search(pattern, command_lower):
                recipients.extend(self.get_batch_emails(batch))
        
        # Section-specific patterns
        section_matches = re.findall(r'section\s+([abc])|([abc])\s+section', command_lower)
        for match in section_matches:
            section = (match[0] or match[1]).upper()
            recipients.extend(self.get_section_emails(section))
        
        # Semester-specific patterns
        semester_matches = re.findall(r'semester\s+(\d+)|sem\s+(\d+)', command_lower)
        for match in semester_matches:
            semester = match[0] or match[1]
            recipients.extend(self.get_semester_emails(semester))
        
        # Individual name extraction
        recipients.extend(self.extract_individual_names(command))
        
        # Remove duplicates and return
        return list(set(filter(lambda x: x and '@' in x, recipients)))
    
    def get_all_students(self) -> List[str]:
        """Get all student emails from all batch files"""
        emails = []
        for batch_df in self.students_dfs.values():
            emails.extend(batch_df['email'].dropna().tolist())
        
        # Also get students from master file if available
        if self.master_df is not None:
            student_emails = self.master_df[self.master_df['role'] == 'student']['email'].dropna().tolist()
            emails.extend(student_emails)
        
        return list(set(emails))
    
    def get_all_faculty(self) -> List[str]:
        """Get all faculty emails from all department files"""
        emails = []
        for dept_df in self.faculty_dfs.values():
            emails.extend(dept_df['email'].dropna().tolist())
        
        # Also get faculty from master file
        if self.master_df is not None:
            faculty_emails = self.master_df[self.master_df['role'] == 'faculty']['email'].dropna().tolist()
            emails.extend(faculty_emails)
        
        return list(set(emails))
    
    def get_all_staff(self) -> List[str]:
        """Get all staff emails"""
        emails = []
        if self.staff_df is not None:
            emails.extend(self.staff_df['email'].dropna().tolist())
        
        # Also get staff from master file
        if self.master_df is not None:
            staff_emails = self.master_df[self.master_df['role'] == 'staff']['email'].dropna().tolist()
            emails.extend(staff_emails)
        
        return list(set(emails))
    
    def get_department_emails(self, department: str) -> List[str]:
        """Get all emails for a specific department"""
        emails = []
        
        # From master file
        if self.master_df is not None:
            dept_mask = self.master_df['department'].str.contains(department, case=False, na=False)
            emails.extend(self.master_df[dept_mask]['email'].dropna().tolist())
        
        # From student files
        for batch_df in self.students_dfs.values():
            if 'department' in batch_df.columns:
                dept_mask = batch_df['department'].str.contains(department, case=False, na=False)
                emails.extend(batch_df[dept_mask]['email'].dropna().tolist())
        
        return list(set(emails))
    
    def get_batch_emails(self, batch: str) -> List[str]:
        """Get emails for a specific batch"""
        if batch in self.students_dfs:
            return self.students_dfs[batch]['email'].dropna().tolist()
        
        # Fallback to master file
        if self.master_df is not None:
            batch_mask = self.master_df['batch'].astype(str) == str(batch)
            return self.master_df[batch_mask]['email'].dropna().tolist()
        
        return []
    
    def get_section_emails(self, section: str, batch: str = None, department: str = None) -> List[str]:
        """Get emails for a specific section"""
        emails = []
        
        # Search in student files
        for batch_year, batch_df in self.students_dfs.items():
            if batch and batch_year != batch:
                continue
            
            if 'section' in batch_df.columns:
                section_mask = batch_df['section'].astype(str).str.upper() == section.upper()
                
                if department:
                    dept_mask = batch_df['department'].str.contains(department, case=False, na=False)
                    section_mask = section_mask & dept_mask
                
                emails.extend(batch_df[section_mask]['email'].dropna().tolist())
        
        return list(set(emails))
    
    def get_semester_emails(self, semester: str) -> List[str]:
        """Get emails for a specific semester"""
        emails = []
        
        # Search in student files
        for batch_df in self.students_dfs.values():
            if 'semester' in batch_df.columns:
                sem_mask = batch_df['semester'].astype(str) == str(semester)
                emails.extend(batch_df[sem_mask]['email'].dropna().tolist())
        
        # Fallback to master file
        if self.master_df is not None and 'semester' in self.master_df.columns:
            sem_mask = self.master_df['semester'].astype(str) == str(semester)
            emails.extend(self.master_df[sem_mask]['email'].dropna().tolist())
        
        return list(set(emails))
    
    def get_faculty_by_designation(self, designations: List[str]) -> List[str]:
        """Get faculty emails by designation"""
        emails = []
        
        # Search in faculty files
        for dept_df in self.faculty_dfs.values():
            if 'designation' in dept_df.columns:
                desig_mask = dept_df['designation'].isin(designations)
                emails.extend(dept_df[desig_mask]['email'].dropna().tolist())
        
        # Search in master file
        if self.master_df is not None and 'designation' in self.master_df.columns:
            desig_mask = self.master_df['designation'].isin(designations)
            emails.extend(self.master_df[desig_mask]['email'].dropna().tolist())
        
        return list(set(emails))
    
    def extract_individual_names(self, command: str) -> List[str]:
        """Extract individual names from command"""
        recipients = []
        command_lower = command.lower()
        
        # Check master file
        if self.master_df is not None:
            for _, contact in self.master_df.iterrows():
                name_parts = str(contact['name']).lower().split()
                
                # Check if any part of name is in command
                for name_part in name_parts:
                    if len(name_part) > 2 and name_part in command_lower:
                        recipients.append(contact['email'])
                        break
        
        return recipients
    
    def validate_email_permissions(self, sender_email: str, recipient_emails: List[str]) -> Dict[str, Any]:
        """Validate sender permissions to email recipients"""
        
        # Get sender information
        sender_info = self.get_contact_info(sender_email)
        if not sender_info:
            return {"allowed": False, "reason": "Sender not found in database"}
        
        sender_designation = sender_info.get('designation', '')
        sender_dept = sender_info.get('department', '')
        
        # Get permission rules for sender
        permissions = self.permissions_config["role_hierarchy"].get(sender_designation, {})
        can_email = permissions.get("can_email", [])
        sender_level = permissions.get("level", 0)
        
        allowed_recipients = []
        blocked_recipients = []
        warnings = []
        
        # Check each recipient
        for recipient_email in recipient_emails:
            recipient_info = self.get_contact_info(recipient_email)
            
            if not recipient_info:
                # External email
                if "external_emails" in self.permissions_config.get("approval_required", {}):
                    if sender_designation in self.permissions_config["approval_required"]["external_emails"]:
                        blocked_recipients.append(recipient_email)
                        continue
                allowed_recipients.append(recipient_email)
                continue
            
            recipient_role = recipient_info.get('role', '')
            recipient_dept = recipient_info.get('department', '')
            
            # Check permissions
            allowed = False
            
            if "everyone" in can_email:
                allowed = True
            elif recipient_role in can_email:
                allowed = True
            elif "department_faculty" in can_email and recipient_role == "faculty" and recipient_dept == sender_dept:
                allowed = True
            elif "department_students" in can_email and recipient_role == "student" and recipient_dept == sender_dept:
                allowed = True
            elif "same_dept_faculty" in can_email and recipient_role == "faculty" and recipient_dept == sender_dept:
                allowed = True
            
            if allowed:
                allowed_recipients.append(recipient_email)
            else:
                blocked_recipients.append(recipient_email)
        
        # Generate warnings
        if len(recipient_emails) > 50:
            warnings.append(f"Large recipient list ({len(recipient_emails)} recipients)")
        
        # Check email limits
        limits = self.permissions_config["email_limits"].get(sender_designation, {})
        if len(allowed_recipients) > limits.get("bulk_limit", 1000):
            warnings.append(f"Exceeds bulk email limit ({limits.get('bulk_limit', 1000)})")
        
        return {
            "allowed": len(blocked_recipients) == 0,
            "allowed_recipients": allowed_recipients,
            "blocked_recipients": blocked_recipients,
            "sender_level": sender_level,
            "warnings": warnings,
            "permission_summary": {
                "can_email": can_email,
                "sender_designation": sender_designation,
                "total_recipients": len(recipient_emails)
            }
        }
    
    def get_contact_info(self, email: str) -> Optional[Dict]:
        """Get detailed contact information for an email"""
        
        # Search in master file first
        if self.master_df is not None:
            contact = self.master_df[self.master_df['email'] == email]
            if not contact.empty:
                return contact.iloc[0].to_dict()
        
        # Search in student files
        for batch_df in self.students_dfs.values():
            contact = batch_df[batch_df['email'] == email]
            if not contact.empty:
                info = contact.iloc[0].to_dict()
                info['role'] = 'student'  # Ensure role is set
                return info
        
        # Search in faculty files  
        for dept_df in self.faculty_dfs.values():
            contact = dept_df[dept_df['email'] == email]
            if not contact.empty:
                info = contact.iloc[0].to_dict()
                info['role'] = 'faculty'  # Ensure role is set
                return info
        
        # Search in staff file
        if self.staff_df is not None:
            contact = self.staff_df[self.staff_df['email'] == email]
            if not contact.empty:
                info = contact.iloc[0].to_dict()
                info['role'] = 'staff'  # Ensure role is set
                return info
        
        return None
    
    def suggest_recipients(self, partial_input: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Suggest recipients based on partial input"""
        suggestions = []
        partial_lower = partial_input.lower()
        
        # Search function
        def search_dataframe(df, additional_info=None):
            if df is None or df.empty:
                return
            
            for _, contact in df.iterrows():
                # Check name, email, department
                name = str(contact.get('name', '')).lower()
                email = str(contact.get('email', '')).lower()
                dept = str(contact.get('department', '')).lower()
                
                if (partial_lower in name or partial_lower in email or partial_lower in dept):
                    suggestion = {
                        'name': contact.get('name', ''),
                        'email': contact.get('email', ''), 
                        'department': contact.get('department', ''),
                        'role': contact.get('role', additional_info.get('role', '') if additional_info else ''),
                        'designation': contact.get('designation', ''),
                        'batch': contact.get('batch', ''),
                        'section': contact.get('section', '')
                    }
                    suggestions.append(suggestion)
                    
                    if len(suggestions) >= limit:
                        return
        
        # Search in all dataframes
        search_dataframe(self.master_df)
        
        for batch_df in self.students_dfs.values():
            search_dataframe(batch_df, {'role': 'student'})
        
        for dept_df in self.faculty_dfs.values():
            search_dataframe(dept_df, {'role': 'faculty'})
        
        search_dataframe(self.staff_df, {'role': 'staff'})
        
        # Remove duplicates by email
        seen_emails = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion['email'] not in seen_emails:
                seen_emails.add(suggestion['email'])
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:limit]
    
    def get_mailing_lists(self) -> Dict[str, List[str]]:
        """Get predefined mailing lists"""
        lists = {
            'all_students': self.get_all_students(),
            'all_faculty': self.get_all_faculty(),
            'all_staff': self.get_all_staff(),
        }
        
        # Add department-specific lists
        departments = ['Computer Science', 'Electronics', 'Mechanical', 'Civil']
        for dept in departments:
            dept_emails = self.get_department_emails(dept)
            if dept_emails:
                lists[f'{dept.lower().replace(" ", "_")}_department'] = dept_emails
        
        # Add batch-specific lists
        for batch in self.students_dfs.keys():
            batch_emails = self.get_batch_emails(batch)
            if batch_emails:
                lists[f'batch_{batch}'] = batch_emails
        
        # Add designation-specific lists
        designations = ['Professor', 'Associate Professor', 'Assistant Professor', 'HOD']
        for designation in designations:
            desig_emails = self.get_faculty_by_designation([designation])
            if desig_emails:
                lists[designation.lower().replace(' ', '_') + 's'] = desig_emails
        
        # Remove empty lists
        return {k: v for k, v in lists.items() if v}
    
    def export_contacts(self, category: str = "all", format: str = "csv") -> str:
        """Export contacts for backup or sharing"""
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        
        if category == "all":
            # Export all contacts to master file
            all_contacts = []
            
            # Collect from all sources
            if self.master_df is not None:
                all_contacts.extend(self.master_df.to_dict('records'))
            
            export_df = pd.DataFrame(all_contacts)
            filename = f"all_contacts_export_{timestamp}.{format}"
            
        elif category == "students":
            all_students = []
            for batch_df in self.students_dfs.values():
                all_students.extend(batch_df.to_dict('records'))
            export_df = pd.DataFrame(all_students)
            filename = f"students_export_{timestamp}.{format}"
            
        elif category == "faculty":
            all_faculty = []
            for dept_df in self.faculty_dfs.values():
                all_faculty.extend(dept_df.to_dict('records'))
            export_df = pd.DataFrame(all_faculty)
            filename = f"faculty_export_{timestamp}.{format}"
        
        else:
            raise ValueError(f"Unknown category: {category}")
        
        # Save file
        export_path = self.base_path / "exports" / filename
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "csv":
            export_df.to_csv(export_path, index=False)
        elif format == "json":
            export_df.to_json(export_path, orient='records', indent=2)
        elif format == "excel":
            export_df.to_excel(export_path, index=False)
        
        logger.info(f"Exported {len(export_df)} contacts to {export_path}")
        return str(export_path)
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {
            "total_contacts": 0,
            "by_role": {"student": 0, "faculty": 0, "staff": 0},
            "by_department": {},
            "by_batch": {},
            "by_designation": {},
            "file_info": {
                "master_file": len(self.master_df) if self.master_df is not None else 0,
                "student_files": len(self.students_dfs),
                "faculty_files": len(self.faculty_dfs),
                "staff_file": len(self.staff_df) if self.staff_df is not None else 0
            },
            "data_quality": {
                "missing_emails": 0,
                "duplicate_emails": 0,
                "invalid_formats": 0
            }
        }
        
        # Count contacts from all sources
        all_emails = set()
        
        # Process master file
        if self.master_df is not None:
            stats["total_contacts"] += len(self.master_df)
            for _, row in self.master_df.iterrows():
                role = row.get('role', 'unknown')
                dept = row.get('department', 'Unknown')
                designation = row.get('designation', 'Unknown')
                email = row.get('email', '')
                
                stats["by_role"][role] = stats["by_role"].get(role, 0) + 1
                stats["by_department"][dept] = stats["by_department"].get(dept, 0) + 1
                stats["by_designation"][designation] = stats["by_designation"].get(designation, 0) + 1
                
                if email:
                    all_emails.add(email)
                else:
                    stats["data_quality"]["missing_emails"] += 1
        
        # Process student files
        for batch, batch_df in self.students_dfs.items():
            stats["total_contacts"] += len(batch_df)
            stats["by_batch"][batch] = len(batch_df)
            stats["by_role"]["student"] += len(batch_df)
            
            for _, row in batch_df.iterrows():
                email = row.get('email', '')
                dept = row.get('department', 'Unknown')
                
                stats["by_department"][dept] = stats["by_department"].get(dept, 0) + 1
                
                if email:
                    if email in all_emails:
                        stats["data_quality"]["duplicate_emails"] += 1
                    else:
                        all_emails.add(email)
                else:
                    stats["data_quality"]["missing_emails"] += 1
        
        # Process faculty files
        for dept, dept_df in self.faculty_dfs.items():
            stats["by_role"]["faculty"] += len(dept_df)
            
            for _, row in dept_df.iterrows():
                email = row.get('email', '')
                designation = row.get('designation', 'Unknown')
                
                stats["by_designation"][designation] = stats["by_designation"].get(designation, 0) + 1
                
                if email:
                    if email in all_emails:
                        stats["data_quality"]["duplicate_emails"] += 1
                    else:
                        all_emails.add(email)
        
        # Process staff file
        if self.staff_df is not None:
            stats["by_role"]["staff"] += len(self.staff_df)
            
            for _, row in self.staff_df.iterrows():
                email = row.get('email', '')
                designation = row.get('designation', 'Unknown')
                
                stats["by_designation"][designation] = stats["by_designation"].get(designation, 0) + 1
                
                if email:
                    if email in all_emails:
                        stats["data_quality"]["duplicate_emails"] += 1
                    else:
                        all_emails.add(email)
        
        # Calculate unique contacts
        stats["unique_contacts"] = len(all_emails)
        
        return stats
    
    def reload_contacts(self):
        """Reload all contact files (useful after external updates)"""
        logger.info("Reloading contact files...")
        
        # Clear existing data
        self.master_df = None
        self.students_dfs.clear()
        self.faculty_dfs.clear()
        self.staff_df = None
        
        # Reload all contacts
        self.load_all_contacts()
        
        logger.info("Contact files reloaded successfully")
    
    def add_contact_to_appropriate_file(self, contact_data: Dict[str, Any]) -> bool:
        """Add a new contact to the appropriate CSV file"""
        try:
            role = contact_data.get('role', '').lower()
            
            if role == 'student':
                # Add to appropriate batch file
                batch = contact_data.get('batch', '')
                if batch:
                    batch_file = self.contacts_path / f"students_{batch}.csv"
                    
                    # Load or create batch file
                    if batch_file.exists():
                        batch_df = pd.read_csv(batch_file)
                    else:
                        batch_df = pd.DataFrame()
                    
                    # Add new contact
                    new_row = pd.DataFrame([contact_data])
                    batch_df = pd.concat([batch_df, new_row], ignore_index=True)
                    batch_df.to_csv(batch_file, index=False)
                    
                    # Update in-memory data
                    self.students_dfs[batch] = batch_df
                    
            elif role == 'faculty':
                # Add to appropriate department file
                dept = contact_data.get('department', '').lower().replace(' ', '_')[:3]  # e.g., 'cse'
                dept_file = self.contacts_path / f"faculty_{dept}.csv"
                
                if dept_file.exists():
                    dept_df = pd.read_csv(dept_file)
                else:
                    dept_df = pd.DataFrame()
                
                new_row = pd.DataFrame([contact_data])
                dept_df = pd.concat([dept_df, new_row], ignore_index=True)
                dept_df.to_csv(dept_file, index=False)
                
                # Update in-memory data
                self.faculty_dfs[dept] = dept_df
                
            elif role == 'staff':
                # Add to staff file
                staff_file = self.contacts_path / "staff_admin.csv"
                
                if staff_file.exists():
                    staff_df = pd.read_csv(staff_file)
                else:
                    staff_df = pd.DataFrame()
                
                new_row = pd.DataFrame([contact_data])
                staff_df = pd.concat([staff_df, new_row], ignore_index=True)
                staff_df.to_csv(staff_file, index=False)
                
                # Update in-memory data
                self.staff_df = staff_df
            
            # Also add to master file
            master_file = self.contacts_path / "contacts_master.csv"
            if master_file.exists():
                master_df = pd.read_csv(master_file)
            else:
                master_df = pd.DataFrame()
            
            new_row = pd.DataFrame([contact_data])
            master_df = pd.concat([master_df, new_row], ignore_index=True)
            master_df.to_csv(master_file, index=False)
            
            # Update in-memory data
            self.master_df = master_df
            
            logger.info(f"Added new {role} contact: {contact_data.get('name', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            return False
    
    def import_contacts_from_csv(self, csv_file_path: str, contact_type: str) -> Dict[str, Any]:
        """Import contacts from external CSV file"""
        try:
            import_df = pd.read_csv(csv_file_path)
            
            results = {
                "total_imported": 0,
                "successful": 0,
                "failed": 0,
                "duplicates": 0,
                "errors": []
            }
            
            for _, row in import_df.iterrows():
                try:
                    # Convert row to dict and add role
                    contact_data = row.to_dict()
                    contact_data['role'] = contact_type
                    
                    # Check for duplicates
                    existing_contact = self.get_contact_info(contact_data.get('email', ''))
                    if existing_contact:
                        results["duplicates"] += 1
                        continue
                    
                    # Add contact
                    if self.add_contact_to_appropriate_file(contact_data):
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        
                    results["total_imported"] += 1
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Row {results['total_imported'] + 1}: {str(e)}")
            
            logger.info(f"Import completed: {results['successful']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            return {"error": str(e)}
    
    def create_department_structure(self, departments: List[Dict[str, str]]) -> bool:
        """Create CSV files for new departments"""
        try:
            for dept_info in departments:
                dept_name = dept_info['name']
                dept_code = dept_info['code'].lower()
                
                # Create faculty file for department
                faculty_file = self.contacts_path / f"faculty_{dept_code}.csv"
                if not faculty_file.exists():
                    faculty_columns = [
                        'name', 'email', 'employee_id', 'designation', 'specialization', 
                        'subjects_taught', 'cabin_no', 'phone', 'years_experience', 'qualification'
                    ]
                    empty_df = pd.DataFrame(columns=faculty_columns)
                    empty_df.to_csv(faculty_file, index=False)
                    logger.info(f"Created faculty file for {dept_name}: {faculty_file}")
                
                # Update institution config
                config_file = self.config_path / "institution_config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    config['departments'][dept_name] = {
                        "code": dept_info['code'],
                        "hod_email": f"hod.{dept_code}@college.edu",
                        "office_location": f"{dept_info['code']} Block"
                    }
                    
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating department structure: {e}")
            return False
    
    def generate_file_template(self, file_type: str, output_path: str = None) -> str:
        """Generate CSV template files for easy data entry"""
        
        templates = {
            "students": {
                "columns": [
                    'name', 'email', 'student_id', 'department', 'batch', 'semester', 
                    'section', 'phone', 'guardian_phone', 'address', 'status'
                ],
                "sample_data": [
                    {
                        'name': 'Sample Student',
                        'email': 'student.2024cse001@college.edu',
                        'student_id': '2024CSE001',
                        'department': 'Computer Science',
                        'batch': '2024',
                        'semester': '1',
                        'section': 'A',
                        'phone': '9876543210',
                        'guardian_phone': '9876543211',
                        'address': 'City, State',
                        'status': 'active'
                    }
                ]
            },
            
            "faculty": {
                "columns": [
                    'name', 'email', 'employee_id', 'designation', 'specialization',
                    'subjects_taught', 'cabin_no', 'phone', 'years_experience', 'qualification'
                ],
                "sample_data": [
                    {
                        'name': 'Dr. Sample Faculty',
                        'email': 'faculty@college.edu',
                        'employee_id': 'FAC001',
                        'designation': 'Professor',
                        'specialization': 'Machine Learning',
                        'subjects_taught': 'ML,AI,Python',
                        'cabin_no': 'C-101',
                        'phone': '9876543210',
                        'years_experience': '10',
                        'qualification': 'PhD Computer Science'
                    }
                ]
            },
            
            "staff": {
                "columns": [
                    'name', 'email', 'employee_id', 'designation', 'department', 
                    'phone', 'office_location', 'status'
                ],
                "sample_data": [
                    {
                        'name': 'Sample Staff',
                        'email': 'staff@college.edu',
                        'employee_id': 'STF001',
                        'designation': 'Admin Assistant',
                        'department': 'Administration',
                        'phone': '9876543210',
                        'office_location': 'Admin Block',
                        'status': 'active'
                    }
                ]
            }
        }
        
        if file_type not in templates:
            raise ValueError(f"Unknown file type: {file_type}")
        
        template_info = templates[file_type]
        
        # Create DataFrame with sample data
        template_df = pd.DataFrame(template_info["sample_data"])
        
        # Generate filename
        if not output_path:
            output_path = self.contacts_path / f"template_{file_type}.csv"
        
        # Save template
        template_df.to_csv(output_path, index=False)
        
        logger.info(f"Generated {file_type} template: {output_path}")
        return str(output_path)