set yuicompressor="c:\wrook\yuicompressor-2.4.1\build\yuicompressor-2.4.1.jar" 
cd scripts
type jquery\jquery.form.js > uncompressed.js
type jquery\jquery.effects.highlight.js >> uncompressed.js
type jquery\jquery.example.js >> uncompressed.js
type jquery\jquery.autogrow.js >> uncompressed.js
type jquery\jquery.expander.js >> uncompressed.js
type jquery\jquery-validate\jquery.validate.js >> uncompressed.js
type jquery\jdimensions\jquery.dimensions.js >> uncompressed.js
type main.js >> uncompressed.js

java -jar %yuicompressor% --type js -o compressed.js uncompressed.js

cd ..\stylesheets
type jquery\jquery.form.js > uncompressed.js

type main.css > uncompressed.css
type template-d.css >> uncompressed.css

java -jar %yuicompressor% --type css -o compressed.css uncompressed.css

cd ..
