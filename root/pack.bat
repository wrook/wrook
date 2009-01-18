@echo off
set yuicompressor="c:\wrook\yuicompressor-2.4.1\build\yuicompressor-2.4.1.jar" 
cd scripts
echo Packaging javascripts...
type jquery\jquery.form.js > unpacked.js
type jquery\jquery.effects.highlight.js >> unpacked.js
type jquery\jquery.example.js >> unpacked.js
type jquery\jquery.autogrow.js >> unpacked.js
type jquery\jquery.expander.js >> unpacked.js
type jquery\jquery.validate.js >> unpacked.js
type jquery\jquery.tooltip.js >> unpacked.js
type main.js >> unpacked.js
echo Compressing javascripts...
java -jar %yuicompressor% --type js -o packed.js unpacked.js
del unpacked.js

cd ..\stylesheets
echo Packaging stylesheets...
type main.css > unpacked.css
type sprites.css >> unpacked.css
type template-d.css >> unpacked.css
type jquery.tooltip.css >> unpacked.css
echo Compressing stylesheets...
java -jar %yuicompressor% --type css -o packed.css unpacked.css
del unpacked.css
echo Done!

cd ..
