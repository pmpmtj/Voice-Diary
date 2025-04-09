# Voice Diary Database Module Diagrams

This document visualizes the relationships and flow between the database modules in the Voice Diary application.

## Setup Database Module Flow

```mermaid
flowchart TD
    subgraph setup_database.py
        A[main] --> B{Check DATABASE_URL env var}
        B -->|Not found| C[Warning and prompt]
        C -->|User confirms| D[initialize_db]
        C -->|User cancels| E[Exit]
        B -->|Found| D
        D -->|Success| F[Log success and exit]
        D -->|Failure| G[Log error and exit]
    end
    
    subgraph db_manager.py
        D --> H[initialize_db]
        H --> I[get_db_url]
        H --> J[Create connection pool]
        H --> K[create_tables]
        K --> L[Execute SQL to create tables]
    end
    
    subgraph db_config.py
        I --> M[get_db_url]
        M --> N[Check env for DATABASE_URL]
        N -->|Not found| O[Get default URL from config]
        N -->|Found| P[Return DATABASE_URL]
        O --> Q[Return default URL]
    end
```

## Database Configuration Module Flow

```mermaid
flowchart TD
    subgraph db_config.py
        A[Module Import] --> B[load_config]
        B --> C{Try to load config.json}
        C -->|Success| D[Return config]
        C -->|Failure| E[Return default config]
        A --> F[Configure logging]
        A --> G[Load environment variables]
        G --> H{Try to load from package}
        H -->|Success| I[Load from package]
        H -->|Failure| J[Try common locations]
        J --> K{Found .env file?}
        K -->|Yes| L[Load from found location]
        K -->|No| M[Continue without .env]
        
        N[get_db_url] --> O{Check DATABASE_URL env var}
        O -->|Found| P[Return DATABASE_URL]
        O -->|Not found| Q[Return default URL from config]
    end
```

## Database Manager Module Flow

```mermaid
flowchart TD
    subgraph db_manager.py
        A[initialize_db] --> B[get_db_url]
        A --> C[Create connection pool]
        A --> D[create_tables]
        D --> E[Create tables if not exist]
        
        F[get_connection] --> G{Connection pool exists?}
        G -->|No| A
        G -->|Yes| H[Get connection from pool]
        
        I[return_connection] --> J[Return connection to pool]
        
        K[save_transcription] --> L[get_connection]
        K --> M[Insert record]
        K --> N[Commit transaction]
        
        O[get_transcription] --> P[get_connection]
        O --> Q[Execute query]
        
        R[save_optimized_transcription] --> S[get_connection]
        R --> T[Insert record]
        R --> U[Commit transaction]
        
        V[close_all_connections] --> W[Close all connections]
    end
    
    subgraph db_config.py
        B --> X[get_db_url]
    end
```

## Overall Module Relationships

```mermaid
flowchart LR
    A[setup_database.py] --> B[db_manager.py]
    B --> C[db_config.py]
    A --> C
    
    A -->|"Calls initialize_db()"| B
    B -->|"Calls get_db_url()"| C
``` 