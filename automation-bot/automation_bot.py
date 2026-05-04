"""
Intelligent Task Automation Bot
Autonomous agent that automates repetitive business tasks using AI and data processing.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

import openai
from pydantic import BaseModel, Field
import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


class TaskType(str, Enum):
    """Supported automation task types."""
    DATA_PROCESSING = "data_processing"
    REPORT_GENERATION = "report_generation"
    DATA_QUALITY = "data_quality"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    ALERT_MANAGEMENT = "alert_management"


class Task(BaseModel):
    """Task definition schema."""
    id: str
    type: TaskType
    description: str
    input_data: Dict[str, Any]
    priority: int = Field(default=1, ge=1, le=5)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "pending"  # pending, processing, completed, failed


class TaskExecutor:
    """Executes automation tasks with AI assistance."""
    
    def __init__(self, config: Dict):
        """Initialize executor with configuration."""
        self.config = config
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.db_engine = create_engine(config.get('database_url', ''))
        
    def add_task(self, task: Task) -> str:
        """Add a task to the queue."""
        logger.info(f"Adding task: {task.id} - {task.description}")
        self.task_queue.append(task)
        return task.id
    
    def get_ai_instruction(self, task: Task) -> str:
        """Generate AI instruction from task using GPT."""
        prompt = f"""
        You are an automation task executor. Analyze this task and provide step-by-step instructions:
        
        Task Type: {task.type}
        Description: {task.description}
        Input Data: {json.dumps(task.input_data, indent=2)}
        
        Provide clear, actionable steps to complete this task. Consider:
        1. Data validation requirements
        2. Error handling strategies
        3. Success criteria
        4. Post-execution verification
        
        Format your response as a JSON-compatible instruction list.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert task automation assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI instruction generation failed: {e}")
            return "Error generating instructions"
    
    def execute_data_processing(self, task: Task) -> Dict[str, Any]:
        """Execute data processing task."""
        logger.info(f"Executing data processing task: {task.id}")
        
        try:
            # Load input data
            input_file = task.input_data.get('input_file')
            output_file = task.input_data.get('output_file')
            transformations = task.input_data.get('transformations', [])
            
            # Read data
            if input_file.endswith('.csv'):
                df = pd.read_csv(input_file)
            elif input_file.endswith('.parquet'):
                df = pd.read_parquet(input_file)
            else:
                raise ValueError(f"Unsupported file format: {input_file}")
            
            logger.info(f"Loaded {len(df)} rows from {input_file}")
            
            # Apply transformations
            for transform in transformations:
                op = transform.get('operation')
                params = transform.get('params', {})
                
                if op == 'remove_duplicates':
                    df = df.drop_duplicates()
                elif op == 'fill_missing':
                    df = df.fillna(params.get('value', 0))
                elif op == 'filter':
                    for col, val in params.items():
                        df = df[df[col] == val]
                elif op == 'aggregate':
                    groupby_cols = params.get('group_by', [])
                    agg_func = params.get('aggregation', 'sum')
                    df = df.groupby(groupby_cols).agg(agg_func).reset_index()
                elif op == 'rename_columns':
                    df = df.rename(columns=params)
            
            logger.info(f"Transformations applied. Result: {len(df)} rows")
            
            # Save result
            if output_file.endswith('.csv'):
                df.to_csv(output_file, index=False)
            elif output_file.endswith('.parquet'):
                df.to_parquet(output_file, index=False)
            
            return {
                'status': 'success',
                'input_rows': len(df),
                'output_file': output_file,
                'transformations_applied': len(transformations)
            }
            
        except Exception as e:
            logger.error(f"Data processing failed: {e}")
            raise
    
    def execute_report_generation(self, task: Task) -> Dict[str, Any]:
        """Generate automated report."""
        logger.info(f"Generating report for task: {task.id}")
        
        try:
            query = task.input_data.get('sql_query')
            report_title = task.input_data.get('report_title', 'Automated Report')
            output_format = task.input_data.get('output_format', 'html')
            
            # Execute query
            df = pd.read_sql(query, self.db_engine)
            
            # Generate summary statistics
            summary = {
                'total_records': len(df),
                'columns': list(df.columns),
                'numeric_summary': df.describe().to_dict(),
                'generated_at': datetime.now().isoformat()
            }
            
            # Create report content
            report_content = f"""
            <h1>{report_title}</h1>
            <p>Generated: {summary['generated_at']}</p>
            <h2>Summary</h2>
            <ul>
                <li>Total Records: {summary['total_records']}</li>
                <li>Columns: {', '.join(summary['columns'])}</li>
            </ul>
            <h2>Data Preview</h2>
            {df.head(10).to_html()}
            """
            
            # Save report
            if output_format == 'html':
                report_file = task.input_data.get('output_file', 'report.html')
                with open(report_file, 'w') as f:
                    f.write(report_content)
            
            return {
                'status': 'success',
                'report_title': report_title,
                'records_analyzed': len(df),
                'output_file': report_file if output_format == 'html' else None
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise
    
    def execute_data_quality_check(self, task: Task) -> Dict[str, Any]:
        """Perform data quality validation."""
        logger.info(f"Executing data quality check: {task.id}")
        
        try:
            query = task.input_data.get('sql_query')
            checks = task.input_data.get('checks', [])
            
            df = pd.read_sql(query, self.db_engine)
            results = {
                'total_records': len(df),
                'checks_performed': [],
                'quality_score': 1.0
            }
            
            for check in checks:
                check_type = check.get('type')
                column = check.get('column')
                params = check.get('params', {})
                
                check_result = {'type': check_type, 'column': column, 'passed': True}
                
                if check_type == 'null_check':
                    null_count = df[column].isnull().sum()
                    max_nulls = params.get('max_null_percent', 10)
                    null_percent = (null_count / len(df)) * 100
                    check_result['passed'] = null_percent <= max_nulls
                    check_result['details'] = f"{null_percent:.2f}% nulls (limit: {max_nulls}%)"
                
                elif check_type == 'range_check':
                    min_val = params.get('min')
                    max_val = params.get('max')
                    out_of_range = ((df[column] < min_val) | (df[column] > max_val)).sum()
                    check_result['passed'] = out_of_range == 0
                    check_result['details'] = f"{out_of_range} values out of range [{min_val}, {max_val}]"
                
                elif check_type == 'uniqueness_check':
                    duplicates = df[column].duplicated().sum()
                    max_dups = params.get('max_duplicates', 0)
                    check_result['passed'] = duplicates <= max_dups
                    check_result['details'] = f"{duplicates} duplicate values"
                
                results['checks_performed'].append(check_result)
                if not check_result['passed']:
                    results['quality_score'] *= 0.9
            
            return results
            
        except Exception as e:
            logger.error(f"Data quality check failed: {e}")
            raise
    
    def execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a single task based on type."""
        task.status = "processing"
        
        try:
            if task.type == TaskType.DATA_PROCESSING:
                result = self.execute_data_processing(task)
            elif task.type == TaskType.REPORT_GENERATION:
                result = self.execute_report_generation(task)
            elif task.type == TaskType.DATA_QUALITY:
                result = self.execute_data_quality_check(task)
            else:
                raise ValueError(f"Unknown task type: {task.type}")
            
            task.status = "completed"
            self.completed_tasks.append(task)
            logger.info(f"Task completed: {task.id}")
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = "pending"
                logger.info(f"Retrying task {task.id} (attempt {task.retry_count})")
            else:
                task.status = "failed"
            
            return {'status': 'failed', 'error': str(e), 'retry_count': task.retry_count}
    
    def process_queue(self) -> List[Dict[str, Any]]:
        """Process all tasks in queue."""
        logger.info(f"Processing {len(self.task_queue)} tasks")
        results = []
        
        # Sort by priority
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)
        
        while self.task_queue:
            task = self.task_queue.pop(0)
            result = self.execute_task(task)
            results.append({
                'task_id': task.id,
                'result': result
            })
        
        return results


if __name__ == '__main__':
    # Example usage
    config = {
        'database_url': 'postgresql://user:pass@localhost/analytics_db',
        'openai_api_key': os.getenv('OPENAI_API_KEY')
    }
    
    executor = TaskExecutor(config)
    
    # Create and execute tasks
    task1 = Task(
        id="dp_001",
        type=TaskType.DATA_PROCESSING,
        description="Clean and deduplicate customer data",
        input_data={
            'input_file': 'raw_customers.csv',
            'output_file': 'cleaned_customers.csv',
            'transformations': [
                {'operation': 'remove_duplicates'},
                {'operation': 'fill_missing', 'params': {'value': 0}},
                {'operation': 'rename_columns', 'params': {'id': 'customer_id'}}
            ]
        }
    )
    
    executor.add_task(task1)
    results = executor.process_queue()
    print(json.dumps(results, indent=2))
