from mangum import Mangum
from app.main import app_

handler = Mangum(app_)