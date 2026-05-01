import os, sys, uvicorn
root = r"c:\Users\Amida\Desktop\Bekzhan1-main\backend\sqlite_query_service"
os.chdir(root)
sys.path.insert(0, root)
uvicorn.run('main:app', host='0.0.0.0', port=8082, reload=False)
