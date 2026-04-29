from fastapi import FastAPI
import os
import uvicorn
from endpoints import sql, create_er_diagram, get_schema
from endpoints import pdd
from fastapi.middleware.cors import CORSMiddleware

print('Checking pdd import...')
try:
    from endpoints import pdd
    print('pdd imported successfully')
except Exception as e:
    print(f'pdd import error: {e}')


app = FastAPI(title='PDD Testing Service', version='1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(sql.router, prefix='/api/sql', tags=['SQL'])
app.include_router(create_er_diagram.router, prefix='/api/diagram', tags=['Diagram'])
app.include_router(get_schema.router, prefix='/api/schema', tags=['Schema'])
app.include_router(pdd.router, prefix='/api/pdd', tags=['PDD'])


@app.get('/')
async def root():
    return {'message': 'PDD Testing Service is running!', 'version': '1.0'}


@app.get('/health')
async def health_check():
    return {'status': 'ok'}


if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='0.0.0.0',
        port=int(os.getenv('PDD_API_PORT', '8082')),
        reload=True,
    )
