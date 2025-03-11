# Command to run qdrant database
```powershell
docker run -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant
```

# Command to run LLM Locally
```powershell
ollama pull deepseek-r1:1.5b
```

```powershell
ollama run deepseek-r1:1.5b
```