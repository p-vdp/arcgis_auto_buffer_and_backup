# auto_buffer
auto_buffer_arcgis

Python app that uses the ArcGIS Online REST API to automatically buffer Survey123 and Collecor entries when called by web hook. Flask app not included.
It also logs any changes to the geodatabase.

I created a flask app to run this program whenever any HTML request is sent to example.com/run.

Be sure to update your survey and buffer layers if you want to use this. You'll also need to register client_id and secret_ids for the program to be able to use the API.
