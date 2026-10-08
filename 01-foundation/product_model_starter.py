from pydantic import BaseModel

# TODO: Create Product model with id, name, price, in_stock

class Product(BaseModel):
    id: int
    name: str
    price: float
    in_stock: bool

product = {'id':1,'name':'sourav','price':102.3,'in_stock':True}
product = Product(**product)

print(product)