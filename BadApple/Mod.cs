using Bang;
using Road;
using Road.Assets;
using Road.StateMachines;
using Road.StateMachines.Computer;
using Murder;
using Murder.Core;
using Murder.Core.Sounds;
using Murder.Core.Geometry;
using Murder.Core.Graphics;
using Murder.Assets.Graphics;
using Murder.Services;
using Murder.Diagnostics;
using System.Numerics;
using System.IO;
using Wayfinder.API;
using Wayfinder.Core;
// using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Audio;
using Microsoft.Xna.Framework.Input;
using HarmonyLib;

namespace XfntyMods
{
    public class BadAppleMod : WayfinderMod
    {
        public override string ID => "xfnty.BadApple";
        public override string Name => "Bad Apple";
        public override string Description => "Bad Apple player for Fiona's computer.";
        public override string Version => "1.0.0";
        public override string Author => "xfnty";

        public static BadAppleMod? Instance { get; private set; }
        private Harmony _harmony;

        public BadAppleMod() {
            _harmony = _harmony = new Harmony(ID);
        }

        public override void Start()
        {
            Instance = this;
            _harmony.PatchAll();
        }

        public override void Stop()
        {
            _harmony.UnpatchAll(_harmony.Id);
        }
    }

    public static class Constants
    {
        public static Guid BadAppleIconSpriteAssetGuid = new Guid("{{ICON_SPRITE_ASSET_GUID}}");
        public static Guid BadAppleSpriteAssetGuid = new Guid("{{SPRITE_ASSET_GUID}}");
        public static Guid BadAppleSoftwareAssetGuid = new Guid("{{SOFTWARE_ASSET_GUID}}");
    }

    [HarmonyPatch(typeof(ComputerStateMachine), "PopulateSoftwareList")]
    public static class Patch1
    {
        private static SpriteAsset? badAppleIconSpriteAsset;
        private static TextureAtlas? badAppleIconAtlas;
        private static TextureAtlas? badAppleAtlas;

        static void Postfix(List<RuntimeSoftware> ____software)
        {
            if (!Game.Data.HasAsset<SoftwareAsset>(Constants.BadAppleSoftwareAssetGuid))
            {
                string badAppleIconSpriteAssetPath = System.IO.Path.Combine(
                    BadAppleMod.Instance!.ModDirectory,
                    "BadAppleIconSpriteAsset.json"
                );
                Patch1.badAppleIconSpriteAsset = (SpriteAsset?)Game.Data.TryLoadAsset(
                    badAppleIconSpriteAssetPath,
                    ""
                );
                GameLogger.Verify(
                    Patch1.badAppleIconSpriteAsset != null && Patch1.badAppleIconSpriteAsset.Guid == Constants.BadAppleIconSpriteAssetGuid,
                    $"BadApple: failed to load '{badAppleIconSpriteAssetPath}' SpriteAsset"
                );
                Game.Data.AddAsset(Patch1.badAppleIconSpriteAsset);

                Patch1.badAppleIconAtlas = Game.Data.TryFetchAtlas(Patch1.badAppleIconSpriteAsset.Atlas);
                GameLogger.Verify(
                    Patch1.badAppleIconAtlas != null,
                    $"BadApple: failed to load '{Patch1.badAppleIconSpriteAsset.Atlas}' TextureAtlas"
                );

                string badAppleSpriteAssetPath = System.IO.Path.Combine(
                    BadAppleMod.Instance!.ModDirectory,
                    "BadAppleSpriteAsset.json"
                );
                SpriteAsset? badAppleSpriteAsset = (SpriteAsset?)Game.Data.TryLoadAsset(
                    badAppleSpriteAssetPath,
                    ""
                );
                GameLogger.Verify(
                    badAppleSpriteAsset != null && badAppleSpriteAsset.Guid == Constants.BadAppleSpriteAssetGuid,
                    $"BadApple: failed to load '{badAppleSpriteAssetPath}' SpriteAsset"
                );
                Game.Data.AddAsset(badAppleSpriteAsset);

                Patch1.badAppleAtlas = Game.Data.TryFetchAtlas(badAppleSpriteAsset.Atlas);
                GameLogger.Verify(
                    Patch1.badAppleAtlas != null,
                    $"BadApple: failed to load '{badAppleSpriteAsset.Atlas}' TextureAtlas"
                );

                string badAppleSoftwareAssetPath = System.IO.Path.Combine(
                    BadAppleMod.Instance!.ModDirectory,
                    "BadAppleSoftwareAsset.json"
                );
                SoftwareAsset? badAppleSoftwareAsset = (SoftwareAsset?)Game.Data.TryLoadAsset(
                    badAppleSoftwareAssetPath,
                    ""
                );
                GameLogger.Verify(
                    badAppleSoftwareAsset != null && badAppleSoftwareAsset.Guid == Constants.BadAppleSoftwareAssetGuid,
                    $"BadApple: failed to load '{badAppleSoftwareAssetPath}' SoftwareAsset"
                );
                Game.Data.AddAsset(badAppleSoftwareAsset);

                Console.WriteLine("BadApple: loaded assets");
            }

            SoftwareAsset? asset = (SoftwareAsset?)Game.Data.TryGetAsset(Constants.BadAppleSoftwareAssetGuid);
            GameLogger.Verify(asset != null, $"BadAppleSoftwareAsset '{Constants.BadAppleSoftwareAssetGuid}' is NULL");

            Guid g = asset.SoftwareIcon.Asset.Guid;

            ____software.Add(
                new RuntimeSoftware(
                    asset,
                    new Point(24 + 52, 10),
                    false
                )
            );
        }
    }

    public class BadAppleWindow : Window
    {
        private SpriteAsset sprite;
        private float StartTime;
        private double Duration;
        private bool Started;
        private SoundEffectInstance? soundInstance;

        private static SoundEffect? sound;

        public BadAppleWindow(Rectangle rectangle, Guid skin, ComputerSounds sounds)
            : base(rectangle, skin, sounds)
        {
            this.Title = "bd.mp4";
            this.sprite = (SpriteAsset)Game.Data.GetAsset(Constants.BadAppleSpriteAssetGuid);
            this.StartTime = Game.Now;
        }

        protected override void DrawImpl(Batch2D batch)
        {
            if (!this.Started)
            {
                if (BadAppleWindow.sound == null)
                {
                    string audioPath = System.IO.Path.Combine(
                        BadAppleMod.Instance!.ModDirectory,
                        "BadApple.wav"
                    );
                    using (FileStream stream = File.OpenRead(audioPath))
                    {
                        BadAppleWindow.sound = SoundEffect.FromStream(stream);
                    }
                }
                this.soundInstance = BadAppleWindow.sound!.CreateInstance();
                this.soundInstance!.Play();
                this.StartTime = Game.NowUnscaled;
                this.Duration = BadAppleWindow.sound!.Duration.TotalSeconds;
                this.Started = true;
            }

            batch.DrawSprite(
                this.sprite,
                new Vector2(),
                new DrawInfo(0.8f){},
                new AnimationInfo("", this.StartTime){ Loop = false }
            );
        }

        protected override WindowResult UpdateImpl(World world, float deltaTime)
        {
            if (
                (this.Started && Game.NowUnscaled - this.StartTime >= this.Duration)
                || Game.Input.Pressed(105, false)
            )
            {
                this.soundInstance?.Stop(immediate: true);
                this.soundInstance?.Dispose();
                return new WindowResult(WindowAction.Close);
            }
            return new WindowResult();
        }
    }

    [HarmonyPatch(typeof(ComputerStateMachine), "UpdateDesktop")]
    public static class ComputerStateMachine_UpdateDesktop_Patch
    {
        static bool Prefix(
            ComputerSounds sounds,
            ref bool __result,
            ComputerStateMachine __instance,
            List<Window> ____windows,
            List<RuntimeSoftware> ____software,
            int ____selectedSoftware
        )
        {
            if (__instance.Busy)
            {
                return true;
            }

            if (Game.Input.Pressed(105))
            {
                RuntimeSoftware s = ____software[____selectedSoftware];
                if (s.Asset.Software != (Software){{SOFTWARE_ENUM_ID}}) {
                    return true;
                }

                ____windows.Add(
                    new BadAppleWindow(
                        s.Asset.WindowSize,
                        __instance.WindowSelectedSprite.Guid,
                        sounds
                    )
                );

                SoundServices.Play(
                    sounds.ProgramOpen,
                    SoundLayer.Any,
                    SoundProperties.None,
                    null,
                    -1,
                    null,
                    null
                );

                Game.Input.Consume(105);
                __result = true;
                return false;
            }

            return true;
        }
    }
}
