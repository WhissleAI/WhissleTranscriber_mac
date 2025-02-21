# WhissleTranscriber_mac
Transcription for Macbook using Whissle API


#### Install python requirements
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-build.txt
```

#### Build
```
python setup.py py2app --no-strip
```

### Build DMG

```
create-dmg \  --volname "WhissleTranscriber" \
  "WhissleTranscriber.dmg" \
  "./dist/WhissleTranscriber.app"
```


