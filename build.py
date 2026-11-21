from cv2 import (
    VideoCapture,
    CAP_PROP_FRAME_WIDTH,
    CAP_PROP_FRAME_HEIGHT,
    CAP_PROP_FRAME_COUNT,
    CAP_PROP_POS_FRAMES,
    CAP_PROP_POS_MSEC,
    CAP_PROP_FPS,
    imread,
    resize,
    INTER_NEAREST,
    imwrite,
)
from PIL import Image
from math import ceil
from gzip import open as gzopen
from time import time
from json import loads as jsloads, dumps as jsdumps
from numpy import array as nparray, sum as npsum, argmin as npargmin, uint8, float32
from shutil import copy2 as copyfile, copytree
from natsort import natsorted
from pathlib import Path
from subprocess import run


NEVERWAY_PATH = 'C:\\Program Files (x86)\\Steam\\steamapps\\common\\Neverway Prologue'
SPRITE_ASSET_GUID = '3bba0079-ad57-4263-96af-f93981e56191'
SOFTWARE_ASSET_GUID = 'dfe88e25-fd2d-45da-a830-813b661be69c'
ICON_SPRITE_ASSET_GUID = '326ba9dc-6c79-4e30-9e66-eec8277fcee3'
SOFTWARE_ENUM_ID = 6969

SAMPLE_FPS = 10
TARGET_WIDTH = 200

USERCONFIG_PATH = Path(__file__).parent / 'userConfig.json'
TMP_DIR = Path(__file__).parent / 'tmp'
FRAMES_DIR = TMP_DIR / 'frames'
PRE_FRAMES_DIR = TMP_DIR / 'pre-frames'
ATLASES_DIR = TMP_DIR / 'atlases'
ASSETS_DIR = TMP_DIR / 'assets'
OUT_ATLASES_DIR = ASSETS_DIR / 'atlas'
VIDEO_PATH = TMP_DIR / 'video.webm'
ASSETS_MARKER = TMP_DIR / 'assets-generated.marker'
OUT_DIR = Path(__file__).parent / 'out'
PROJECT_DIR = Path(__file__).parent / 'BadApple'
SPRITE_ASSET_PATH = ASSETS_DIR / 'BadAppleSpriteAsset.json'
SOFTWARE_ASSET_PATH = ASSETS_DIR / 'BadAppleSoftwareAsset.json'
ATLAS_PATH = OUT_ATLASES_DIR / 'BadAppleAtlas.json'
AUDIO_PATH = TMP_DIR / 'BadApple.wav'

VIDEO_URL = 'https://www.youtube.com/watch?v=FtutLA63Cp8'
# VIDEO_URL = 'https://www.youtube.com/watch?v=fp-52d4HxtY'

PALETTE = [
    '000000',
    '2c2c4d',
    '494d7e',
    '706a9c',
    '9f9fd6',
    'ebb9e4',
    'fff7db',
    '76fff4',
    'ff6eed',
    '89ae80',
    '6b1336',
    '692e61',
    'a42f27',
]


def generate_assets():
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    if not VIDEO_PATH.exists():
        print('downloading video ...')
        run(
            ['yt-dlp', '-o', str(VIDEO_PATH), '-f', 'bv[height<=360]+ba/b[height<=360]', VIDEO_URL],
            check=True,
        )

    print('extracting audio ...')
    run(
        [
            'ffmpeg',
            '-y',
            '-i',
            str(VIDEO_PATH),
            '-vn',
            '-c:a',
            'pcm_s16le',
            str(AUDIO_PATH)
        ],
        check=True
    )

    print('extracting frames ...')
    PRE_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    run(
        [
            'ffmpeg',
            '-y',
            '-i',
            str(VIDEO_PATH),
            '-vf',
            f'fps={SAMPLE_FPS}',
            str(PRE_FRAMES_DIR / '%04d.png')
        ],
        check=True
    )

    print('reencoding frames ...')
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    capture = VideoCapture(str(VIDEO_PATH))
    assert capture.isOpened()
    capture_width = capture.get(CAP_PROP_FRAME_WIDTH)
    capture_height = capture.get(CAP_PROP_FRAME_HEIGHT)
    capture_fps = capture.get(CAP_PROP_FPS)
    capture.release()

    frame_paths = sorted(PRE_FRAMES_DIR.iterdir())
    capture_frame_count = len(frame_paths)

    palette = nparray(
        [(int(c[4:6], 16), int(c[2:4], 16), int(c[:2], 16)) for c in PALETTE],
        dtype=uint8,
    ).astype(float32)
    i, j = 0, 0
    last_status = time()
    for i, frame_path in enumerate(frame_paths):
        frame = imread(str(frame_path))

        scale = TARGET_WIDTH / capture_width
        frame = resize(frame, None, fx=scale, fy=scale, interpolation=INTER_NEAREST)

        pixels = frame.reshape(-1, 3).astype(float32)
        dists = npsum(((pixels[:, None, :] - palette[None, :, :]) ** 2), axis=2)
        nearest_indices = npargmin(dists, axis=1)
        frame = palette[nearest_indices].reshape(frame.shape)

        imwrite(str(FRAMES_DIR / f'{j}.png'), frame)

        i += capture_fps / SAMPLE_FPS
        j += 1

        if time() - last_status >= 1:
            print(f'{round(i / capture_frame_count * 100)}%')
            last_status = time()

    print('packing frames ...')
    ATLASES_DIR.mkdir(parents=True, exist_ok=True)

    last_status = time()
    atlas_width, atlas_height = 8192, 8192
    frame_width = TARGET_WIDTH
    frame_height = capture_height * (TARGET_WIDTH / capture_width)
    frames_per_atlas_width = atlas_width // frame_width
    frames_per_atlas_height = atlas_height // frame_height
    frames_per_atlas = frames_per_atlas_width * frames_per_atlas_height
    frames = {}
    atlases_saved = 0
    atlas = Image.new('RGB', (atlas_width, atlas_height))
    all_frame_paths = natsorted(FRAMES_DIR.iterdir())
    for i, frame_path in enumerate(all_frame_paths):
        if frames and i % frames_per_atlas == 0:
            atlas_path = ATLASES_DIR / f'atlas{atlases_saved:03}.qoi'
            atlas_path.with_suffix('.json').open('w').write(jsdumps(
                {
                    'frames': frames,
                    'meta': {
                        'size': { 'w': atlas_width, 'h': atlas_height },
                        'image': str(atlas_path),
                    }
                },
                indent=2
            ))
            atlas.save(str(atlas_path))
            atlas = Image.new('RGB', (atlas_width, atlas_height))
            frames = {}
            atlases_saved += 1
        x = int(frame_width * (i % frames_per_atlas % frames_per_atlas_width))
        y = int(frame_height * (i % frames_per_atlas // frames_per_atlas_width))
        w = int(frame_width)
        h = int(frame_height)
        atlas.paste(Image.open(str(frame_path)), (x, y))
        frames[frame_path.name] = { 'frame': { 'x': x, 'y': y, 'w': w, 'h': h } }
        if time() - last_status >= 1:
            print(f'{round(i / len(all_frame_paths) * 100)}%')
            last_status = time()
    if frames:
        atlas_path = ATLASES_DIR / f'atlas{atlases_saved:03}.qoi'
        atlas_path.with_suffix('.json').open('w').write(jsdumps(
            {
                'frames': frames,
                'meta': {
                    'size': { 'w': atlas_width, 'h': atlas_height },
                    'image': str(atlas_path),
                }
            },
            indent=2
        ))
        atlas.save(str(atlas_path))
        atlas = Image.new('RGB', (atlas_width, atlas_height))
        frames = {}
        atlases_saved += 1

    print('generating Murder assets ...')
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_ATLASES_DIR.mkdir(parents=True, exist_ok=True)

    sprite_asset = {
        '$type': 'Murder.Assets.Graphics.SpriteAsset',
        'Atlas': 'BadAppleAtlas',
        'Size': { 'X': int(capture_width), 'Y': int(capture_height) },
        'Name': 'BadAppleSprite',
        'Guid': SPRITE_ASSET_GUID,
        'Animations': {
            '': {
                'Frames': [],
                'FramesDuration': [],
            },
        },
        'Frames': []
    }

    atlas_asset = {
        'AtlasId': sprite_asset['Atlas'],
        'entries': {},
    }

    software_asset = {
        '$type': 'Road.Assets.SoftwareAsset',
        'LocalizedFileName': {
            'OverrideText': 'bd.mp4',
        },
        'SoftwareIcon': {
            'Guid': ICON_SPRITE_ASSET_GUID,
        },
        'WindowSize': {
            'X': 30,
            'Y': 10,
            'Width': int(TARGET_WIDTH),
            'Height': int(ceil(capture_height * (TARGET_WIDTH / capture_width))),
        },
        'Software': SOFTWARE_ENUM_ID,
        'Name': 'BadAppleSoftware',
        'Guid': SOFTWARE_ASSET_GUID,
    }

    last_status = time()
    atlases = [jsloads(p.open().read()) for p in natsorted(ATLASES_DIR.glob('*.json'))]
    for i, atlas in enumerate(atlases):
        imp = Path(atlas['meta']['image'])
        with gzopen(str(OUT_ATLASES_DIR / f'{sprite_asset['Atlas']}{i:03}.qoi.gz'), 'wb') as f:
            f.write(imp.open('rb').read())

        atlas_width = atlas['meta']['size']['w']
        atlas_height = atlas['meta']['size']['h']
        for j, frame in enumerate(atlas['frames'].values()):
            frame = frame['frame']
            sprite_asset['Frames'].append({
                'AtlasIndex': i,
                'Name': f'BadApple_{i}_{j}',
                'Size': {
                    'X': int(sprite_asset['Size']['X']),
                    'Y': int(sprite_asset['Size']['Y']),
                },
                'SourceRectangle': {
                    'X': int(frame['x']),
                    'Y': int(frame['y']),
                    'Width': int(frame['w']),
                    'Height': int(frame['h']),
                },
                'UV': {
                    'X': frame['x'] / atlas_width,
                    'Y': frame['y'] / atlas_height,
                    'Width': frame['w'] / atlas_width,
                    'Height': frame['h'] / atlas_height,
                },
                'TrimArea': {
                    'Width': int(frame['w']),
                    'Height': int(frame['h']),
                },
                'AtlasId': sprite_asset['Atlas'],
            })
            sprite_asset['Animations']['']['Frames'].append(len(sprite_asset['Frames']) - 1)
            sprite_asset['Animations']['']['FramesDuration'].append(1 / SAMPLE_FPS * 1000)
            atlas_asset['entries'][sprite_asset['Frames'][-1]['Name']] = sprite_asset['Frames'][-1]

        if time() - last_status >= 1:
            print(f'{round(i / len(all_frame_paths) * 100)}%')
            last_status = time()

    sprite_asset['Animations']['']['AnimationDuration'] = 1 / SAMPLE_FPS * len(sprite_asset['Animations']['']['Frames'])

    SPRITE_ASSET_PATH.open('w').write(jsdumps(sprite_asset, indent=4))
    SOFTWARE_ASSET_PATH.open('w').write(jsdumps(software_asset, indent=4))
    ATLAS_PATH.open('w').write(jsdumps(atlas_asset, indent=4))


if __name__ == '__main__':
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    if USERCONFIG_PATH.exists():
        uc = jsloads(USERCONFIG_PATH.open().read())
        NEVERWAY_PATH = uc['NEVERWAY_PATH'] if 'NEVERWAY_PATH' in uc else NEVERWAY_PATH

    if not ASSETS_MARKER.exists():
        generate_assets()
        ASSETS_MARKER.touch()
    # generate_assets()

    print('building DLL ...')
    tp = TMP_DIR / PROJECT_DIR.name
    copytree(str(PROJECT_DIR), str(tp), dirs_exist_ok=True)
    csproj = (tp / 'BadApple.csproj').open().read()
    csproj = csproj.replace('{{NEVERWAY_PATH}}', str(NEVERWAY_PATH))
    (tp / 'BadApple.csproj').open('w').write(csproj)
    modcs = (tp / 'Mod.cs').open().read()
    modcs = modcs.replace('{{SPRITE_ASSET_GUID}}', str(SPRITE_ASSET_GUID))
    modcs = modcs.replace('{{SOFTWARE_ASSET_GUID}}', str(SOFTWARE_ASSET_GUID))
    modcs = modcs.replace('{{ICON_SPRITE_ASSET_GUID}}', str(ICON_SPRITE_ASSET_GUID))
    modcs = modcs.replace('{{SOFTWARE_ENUM_ID}}', str(SOFTWARE_ENUM_ID))
    (tp / 'Mod.cs').open('w').write(modcs)
    run(
        ['dotnet', 'build', str(tp)],
        check=True,
    )

    print('packaging ...')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mods = (OUT_DIR / 'Mods')
    mods.mkdir(parents=True, exist_ok=True)
    atlasdir = (OUT_DIR / 'ModdedCoreFiles' / 'resources' / 'atlas')
    atlasdir.mkdir(parents=True, exist_ok=True)
    copyfile(str(tp / 'bin' / 'BadApple.dll'), mods)
    copyfile(str(SPRITE_ASSET_PATH), mods)
    copyfile(str(SOFTWARE_ASSET_PATH), mods)
    copyfile(str(PROJECT_DIR / 'BadAppleIconAtlas.json'), str(atlasdir))
    copyfile(str(PROJECT_DIR / 'BadAppleIconAtlas000.qoi.gz'), str(atlasdir))
    copyfile(str(PROJECT_DIR / 'BadAppleIconSpriteAsset.json'), str(mods))
    copytree(str(OUT_ATLASES_DIR), str(atlasdir), dirs_exist_ok=True)
    copyfile(str(AUDIO_PATH), str(mods))

    print('installing ...')
    copytree(str(OUT_DIR), NEVERWAY_PATH, dirs_exist_ok=True)

    print(f'installed to "{NEVERWAY_PATH}"')

    print()
    print('running dnSpy:')
    print(f'  Executable: {str(Path(NEVERWAY_PATH) / "ModdedCoreFiles" / "Neverway.dll")}')
    print(f'  Working Directory: {str(Path(NEVERWAY_PATH) / "ModdedCoreFiles")}')
    print('  Environtment:')
    print(f'    DOTNET_ROOT {str(Path(NEVERWAY_PATH) / "Wayfinder")}')
    print(f'    DOTNET_STARTUP_HOOKS {str(Path(NEVERWAY_PATH) / "Wayfinder" / "Wayfinder.Patcher.dll")}')
    print('  Host arguments:')
    print(f'    --runtimeConfig "{str(Path(NEVERWAY_PATH) / "ModdedCoreFiles" / "Neverway.runtimeconfig.json")}"')
    print(f'    --depsfile "{str(Path(NEVERWAY_PATH) / "ModdedCoreFiles" / "Neverway.deps.json")}"')
    print(f'    --additionalProbingPath "{str(Path(NEVERWAY_PATH) / "ModdedCoreFiles")}"')
