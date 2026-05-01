import os, sys, uvicorn
root = r"c:\Users\Amida\Desktop\Bekzhan1-main\backend\sqlite_query_service"
os.chdir(root)
sys.path.insert(0, root)
uvicorn.run('main:app', host='127.0.0.1', port=8099, reload=False)
