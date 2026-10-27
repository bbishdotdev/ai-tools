def tokens(text):
    return set(text.lower().split())


class Catalog:
    def __init__(self, products):
        self.products = {product["id"]: dict(product) for product in products}

    def update(self, product_id, **fields):
        self.products[product_id].update(fields)

    def search(self, query):
        wanted = tokens(query)
        return sorted(product_id for product_id, product in self.products.items()
                      if wanted and wanted <= tokens(product["name"]))
