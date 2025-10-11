# canvas-download
Canvas Download automatically downloads Canvas modules/files into a local directory for offline access. A file called config.json will be created during the first run of the utility and no files will be downloaded in this run. config.json will define whether to download "files" or "modules" for a particular course. To use this command line utility, create the following files as listed below in the same directory as you want the canvas files to be downloaded to.

## login.json
{
    "API_URL": "",
    "API_KEY": ""
}