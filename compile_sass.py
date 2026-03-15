import sass

# Compile Sass to CSS
css = sass.compile(filename='static/style.scss', output_style='expanded')
with open('static/style.css', 'w') as f:
    f.write(css)

print("Sass compiled to CSS successfully!")