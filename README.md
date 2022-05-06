# Micro Rest
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## Instalación

```bash
pip install git+https://github.com/lastseal/micro-rest
```

## Uso Básico

```python
from micro import rest

@rest.api("GET", "/api/hello")
def main(req):
    return "Hello World"
```

```python
from micro import rest

@rest.api("GET", "/api/<int:id>")
def main(req):
    return f"id={req.params.id}"
```

```python
from micro import rest

@rest.api("GET", "/api/find?id=1")
def main(req):
    return f"id={req.args.get('id')}"
```

```python
from micro import rest

@rest.api("GET", "/api/find?id=1")
def main(req):
    return {
      "id": 1
    }
```

```python
from micro import rest

@rest.api("POST", "/api/update")
def main(req):
    data = req.json
    return {"data": data}
```

```python
from micro import rest

@rest.api("GET", "/api/find")
def main(req):
    raise Exception({"status": 400, "message": "Error de usuario"})
```

