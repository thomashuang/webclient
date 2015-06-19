# webclient
python web cleint

## Example

  c = WebClient('https://github.com')
  c.get('/')
  print c.status_code
  print c.content
