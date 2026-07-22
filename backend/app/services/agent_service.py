import json
import logging
import os
from litellm import completion
from dotenv import load_dotenv

# Force load the .env file and override any stale system variables
load_dotenv(dotenv_path="C:\\Users\\avenxkat\\industrial-copilot\\backend\\.env", override=True)

from app.config import settings
from app.services.rag_anything_service import query_multimodal_rag
from app.services.machine_telemetry import query_logs, detect_anomalies_isolation_tree, get_machine_sensors
from app.services.sqlite_agent_service import list_uploaded_sqlite_dbs, get_database_schema, query_database, run_isolation_forest_on_database

logger = logging.getLogger(__name__)

# Define the JSON schemas for the tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_machine_sensors",
            "description": "Queries the TSDB to instantly find all unique sensor types installed on a specific machine. Use this to figure out what sensors exist if the user doesn't specify one.",
            "parameters": {
                "type": "object",
                "properties": {
                    "machine_id": {
                        "type": "string",
                        "description": "The ID of the machine, e.g., PUMP-101A"
                    }
                },
                "required": ["machine_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies_isolation_tree",
            "description": "Uses Machine Learning (Isolation Forest) to mathematically detect anomalies/outliers in raw numeric sensor data. Use this when the user asks if a machine is acting weird or wants you to detect anomalies in a specific sensor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "machine_id": {
                        "type": "string",
                        "description": "The ID of the machine, e.g., PUMP-101A"
                    },
                    "sensor_type": {
                        "type": "string",
                        "description": "The type of sensor to analyze (e.g., Vibration, Temperature, Pressure)"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "The number of hours to look back (default 24)"
                    }
                },
                "required": ["machine_id", "sensor_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_machine_logs",
            "description": "Queries the Machine Time-Series Database (TSDB) for sensor logs and error codes over a specific time range. Use this when a technician asks about a specific machine's status, errors, or sensor readings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "machine_id": {
                        "type": "string",
                        "description": "The ID of the machine, e.g., PUMP-101A or COMPRESSOR-B"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "The number of hours to look back (default 24)"
                    },
                    "error_only": {
                        "type": "boolean",
                        "description": "If true, only returns logs that have an error status code"
                    }
                },
                "required": ["machine_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_graph",
            "description": "Queries the Neo4j Knowledge Graph. Use this to find step-by-step instructions to fix a specific error code, perform maintenance, OR to answer any general questions about the system, its problem statement, or the documents ingested into it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g., 'How to fix ERR_HIGH_TEMP on PUMP-101A' or 'What problem statement are we solving?'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_uploaded_sqlite_dbs",
            "description": "Lists all user-uploaded SQLite databases.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_database_schema",
            "description": "Uses LangChain to extract a highly readable text representation of the database schema (DDL + sample rows). Always use this first before writing SQL queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "db_filename": {
                        "type": "string",
                        "description": "The filename of the uploaded database."
                    }
                },
                "required": ["db_filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Executes a read-only SELECT query on an uploaded SQLite database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "db_filename": {
                        "type": "string",
                        "description": "The filename of the uploaded database."
                    },
                    "query": {
                        "type": "string",
                        "description": "The SELECT query to execute."
                    }
                },
                "required": ["db_filename", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_isolation_forest_on_database",
            "description": "Runs an Isolation Forest model to detect mathematical anomalies in a specific numeric column of an uploaded SQLite database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "db_filename": {
                        "type": "string",
                        "description": "The filename of the uploaded database."
                    },
                    "table_name": {
                        "type": "string",
                        "description": "The table to analyze."
                    },
                    "column_name": {
                        "type": "string",
                        "description": "The numeric column to detect anomalies in."
                    }
                },
                "required": ["db_filename", "table_name", "column_name"]
            }
        }
    }
]

SYSTEM_PROMPT = """
You are the Expert Industrial Copilot for field technicians.
You have access to a Machine Telemetry Database (TSDB), Machine Learning Tools (Isolation Forest), a Neo4j Knowledge Graph, and arbitrary SQLite databases uploaded by users.

Workflow:
1. If the user asks about a machine's status or a recent error, use `query_machine_logs`.
2. If the user wants to know if a machine is acting weird but DOES NOT specify a sensor, autonomously use `get_machine_sensors` to find out what sensors exist.
3. Then, use `detect_anomalies_isolation_tree` to mathematically detect sensor outliers on those sensors!
4. If the user asks how to fix an error, perform maintenance, OR asks ANY general question about the system, financial data, company reports, or any topic not related to machine logs, YOU MUST use `search_knowledge_graph`. Do NOT claim you lack access to real-time data. Assume the document exists in the graph.
5. If the user wants you to analyze an uploaded SQLite database, first use `list_uploaded_sqlite_dbs` to find available databases. Then use `get_database_schema` to learn the DDL and table contents. Finally, use `query_database` to fetch insights, or `run_isolation_forest_on_database` to detect anomalies!
6. If necessary, use MULTIPLE tools sequentially to solve the problem!

CRITICAL TOOL CALLING INSTRUCTION: You must strictly use the native JSON tool-calling API. NEVER output raw text tags like `<function=...>` in your response.

CRITICAL RESPONSE INSTRUCTION: 
1. Always provide clear, concise instructions. Do not make up repair steps or facts; rely entirely on the tools and the Knowledge Graph.
2. YOU MUST CITE YOUR SOURCES PERFECTLY. Whenever you provide an answer based on the Knowledge Graph or a database, explicitly state the document name, database name, or source file where you found the information. Format citations clearly, e.g., "[Source: NVIDIA_10K.pdf]".
"""

async def execute_tool(tool_call):
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    
    logger.info(f"Executing tool: {name} with args: {args}")
    
    if name == "get_machine_sensors":
        machine_id = args.get("machine_id")
        sensors = get_machine_sensors(machine_id)
        if not sensors:
            return f"No sensors found for machine {machine_id}."
        return json.dumps({"sensors": sensors})

    elif name == "detect_anomalies_isolation_tree":
        machine_id = args.get("machine_id")
        sensor_type = args.get("sensor_type")
        hours = args.get("hours", 24)
        anomalies = detect_anomalies_isolation_tree(machine_id, sensor_type, hours)
        if not anomalies:
            return f"No mathematical anomalies detected for {machine_id} {sensor_type} in the last {hours} hours."
        return json.dumps(anomalies)

    elif name == "query_machine_logs":
        machine_id = args.get("machine_id")
        hours = args.get("hours", 24)
        error_only = args.get("error_only", False)
        logs = query_logs(machine_id, hours, error_only)
        if not logs:
            return f"No logs found for machine {machine_id} in the last {hours} hours."
        return json.dumps(logs)
        
    elif name == "search_knowledge_graph":
        query = args.get("query")
        # Ensure lightrag is initialized if needed
        answer = await query_multimodal_rag(query)
        return str(answer)
        
    elif name == "list_uploaded_sqlite_dbs":
        return json.dumps({"uploaded_databases": list_uploaded_sqlite_dbs()})
        
    elif name == "get_database_schema":
        db_filename = args.get("db_filename")
        return get_database_schema(db_filename)  # Returns a string from Langchain
        
    elif name == "query_database":
        db_filename = args.get("db_filename")
        query = args.get("query")
        return json.dumps(query_database(db_filename, query))
        
    elif name == "run_isolation_forest_on_database":
        db_filename = args.get("db_filename")
        table_name = args.get("table_name")
        column_name = args.get("column_name")
        return json.dumps(run_isolation_forest_on_database(db_filename, table_name, column_name))
        
    return f"Error: Tool {name} not found."

async def chat_with_agent(conversation_history: list[dict]):
    """
    Main loop for the ReAct agent. It runs until it provides a final answer.
    Takes an array of historical messages from the frontend.
    """
    # 1. Initialize the message list with the System Prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 2. Append only the last 4 messages from the conversation history to save tokens
    # Groq free tier has a strict TPM limit. Long histories cause instant rate limits.
    recent_history = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
    for msg in recent_history:
        # Sanitize incoming history so old massive tool outputs don't crash the limit
        if msg.get("content") and isinstance(msg["content"], str) and len(msg["content"]) > 1000:
            msg["content"] = msg["content"][:1000] + "\n...[TRUNCATED TO SAVE TOKENS]..."
        messages.append(msg)
        
    model = settings.LLM_MODEL
    
    print(f"Agent received history of length {len(conversation_history)}")
    
    # ReAct Loop (max 10 steps)
    for step in range(10):
        response = completion(
            model=model,
            messages=messages,
            tools=TOOLS,
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY
        )
        
        response_message = response.choices[0].message
        
        # If the model wants to call a tool
        if getattr(response_message, 'tool_calls', None):
            # Convert to dict to prevent pydantic serialization warnings in litellm
            msg_dict = response_message.model_dump() if hasattr(response_message, 'model_dump') else dict(response_message)
            messages.append(msg_dict)
            
            for tool_call in response_message.tool_calls:
                tool_result = await execute_tool(tool_call)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_result
                })
        else:
            # The model returned a final text response
            content = getattr(response_message, 'content', None)
            return content if content else "Sorry, I couldn't generate a response. Please try again."
            
    return "Agent reached maximum steps without a final answer."
