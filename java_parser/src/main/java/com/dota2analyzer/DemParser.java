package com.dota2analyzer;

import skadistats.clarity.model.Entity;
import skadistats.clarity.model.FieldPath;
import skadistats.clarity.processor.entities.Entities;
import skadistats.clarity.processor.entities.UsesEntities;
import skadistats.clarity.processor.entities.OnEntityCreated;
import skadistats.clarity.processor.entities.OnEntityUpdated;
import skadistats.clarity.processor.gameevents.OnCombatLogEntry;
import skadistats.clarity.model.CombatLogEntry;
import skadistats.clarity.wire.dota.common.proto.DOTACombatLog.DOTA_COMBATLOG_TYPES;
import skadistats.clarity.processor.reader.OnTickEnd;
import skadistats.clarity.processor.runner.Context;
import skadistats.clarity.processor.runner.SimpleRunner;
import skadistats.clarity.source.MappedFileSource;

import java.util.*;
import java.io.FileWriter;
import java.io.IOException;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

@UsesEntities
public class DemParser {
    
    private int tickCount = 0;
    private Map<Integer, HeroData> heroes = new HashMap<>();
    private Map<Integer, String> itemEntities = new HashMap<>();
    private List<DeathEvent> deaths = new ArrayList<>();
    private Map<Integer, Long> playerIdToSteamId = new HashMap<>();
    
    private static final Map<String, String> ITEM_CN = new HashMap<>();
    static {
        ITEM_CN.put("CDOTA_Item_MagicWand", "大魔棒");
        ITEM_CN.put("CDOTA_Item_MagicStick", "魔棒");
        ITEM_CN.put("CDOTA_Item_Bracer", "护腕");
        ITEM_CN.put("CDOTA_Item_Wraith_Band", "系带");
        ITEM_CN.put("CDOTA_Item_NullTalisman", "挂件");
        ITEM_CN.put("CDOTA_Item_BootsOfTravel", "远行鞋");
        ITEM_CN.put("CDOTA_Item_PowerTreads", "假腿");
        ITEM_CN.put("CDOTA_Item_PhaseBoots", "相位鞋");
        ITEM_CN.put("CDOTA_Item_TranquilBoots", "静谧鞋");
        ITEM_CN.put("CDOTA_Item_Blink", "闪烁匕首");
        ITEM_CN.put("CDOTA_Item_BlinkDagger", "闪烁匕首");
        ITEM_CN.put("CDOTA_Item_TeleportScroll", "回城卷轴");
        ITEM_CN.put("CDOTA_Item_Tango", "树之祭祀");
        ITEM_CN.put("CDOTA_Item_QuellingBlade", "压制之刃");
        ITEM_CN.put("CDOTA_Item_Circlet", "圆环");
        ITEM_CN.put("CDOTA_Item_Gauntlets", "力量手套");
        ITEM_CN.put("CDOTA_Item_IronwoodBranch", "铁树枝干");
        ITEM_CN.put("CDOTA_Item_Enchanted_Mango", "魔法芒果");
        ITEM_CN.put("CDOTA_Item_Faerie_Fire", "仙灵之火");
        ITEM_CN.put("CDOTA_Item_Mantle", "精灵布带");
        ITEM_CN.put("CDOTA_Item_Slippers", "敏捷便鞋");
        ITEM_CN.put("CDOTA_Item_Blight_Stone", "枯萎之石");
        ITEM_CN.put("CDOTA_Item_OrbOfVenom", "淬毒之珠");
        ITEM_CN.put("CDOTA_Item_WindLace", "风灵之纹");
        ITEM_CN.put("CDOTA_Item_Cloak", "抗魔斗篷");
        ITEM_CN.put("CDOTA_Item_GhostScepter", "幽魂权杖");
        ITEM_CN.put("CDOTA_Item_Gloves", "加速手套");
        ITEM_CN.put("CDOTA_Item_BeltOfStrength", "力量腰带");
        ITEM_CN.put("CDOTA_Item_BandOfElvenskin", "精灵皮靴");
        ITEM_CN.put("CDOTA_Item_Robe", "法师长袍");
        ITEM_CN.put("CDOTA_Item_OgreAxe", "食人魔之斧");
        ITEM_CN.put("CDOTA_Item_BladeOfAlacrity", "欢欣之刃");
        ITEM_CN.put("CDOTA_Item_StaffOfWizardry", "魔力法杖");
        ITEM_CN.put("CDOTA_Item_DemonEdge", "恶魔刀锋");
        ITEM_CN.put("CDOTA_Item_MithrilHammer", "秘银锤");
        ITEM_CN.put("CDOTA_Item_Javelin", "标枪");
        ITEM_CN.put("CDOTA_Item_Broadsword", "阔剑");
        ITEM_CN.put("CDOTA_Item_BladesOfAttack", "攻击之爪");
        ITEM_CN.put("CDOTA_Item_Chainmail", "锁子甲");
        ITEM_CN.put("CDOTA_Item_HelmOfIronWill", "铁意头盔");
        ITEM_CN.put("CDOTA_Item_Boots", "速度之靴");
        ITEM_CN.put("CDOTA_Item_GemOfTrueSight", "真视宝石");
        ITEM_CN.put("CDOTA_Item_SentryWard", "岗哨守卫");
        ITEM_CN.put("CDOTA_Item_ObserverWard", "侦查守卫");
        ITEM_CN.put("CDOTA_Item_SmokeOfDeceit", "诡计之雾");
        ITEM_CN.put("CDOTA_Item_Dust", "显影之尘");
        ITEM_CN.put("CDOTA_Item_Blood_Grenade", "血榴弹");
        ITEM_CN.put("CDOTA_Item_Flask", "治疗药膏");
        ITEM_CN.put("CDOTA_Item_Clarity", "净化药水");
        ITEM_CN.put("CDOTA_Item_ForceStaff", "原力法杖");
        ITEM_CN.put("CDOTA_Item_Cyclone", "Eul的神圣法杖");
        ITEM_CN.put("CDOTA_Item_RodOfAtos", "阿托斯之棍");
        ITEM_CN.put("CDOTA_Item_VeilOfDiscord", "纷争面纱");
        ITEM_CN.put("CDOTA_Item_GlimmerCape", "微光披风");
        ITEM_CN.put("CDOTA_Item_AetherLens", "以太透镜");
        ITEM_CN.put("CDOTA_Item_LotusOrb", "清莲宝珠");
        ITEM_CN.put("CDOTA_Item_SolarCrest", "炎阳纹章");
        ITEM_CN.put("CDOTA_Item_MedallionOfCourage", "勇气勋章");
        ITEM_CN.put("CDOTA_Item_UrnOfShadows", "影之灵龛");
        ITEM_CN.put("CDOTA_Item_SpiritVessel", "魂之灵瓮");
        ITEM_CN.put("CDOTA_Item_Vladmir", "弗拉迪米尔的祭品");
        ITEM_CN.put("CDOTA_Item_Mekansm", "梅肯斯姆");
        ITEM_CN.put("CDOTA_Item_GuardianGreaves", "卫士胫甲");
        ITEM_CN.put("CDOTA_Item_Pipe", "洞察烟斗");
        ITEM_CN.put("CDOTA_Item_HoodOfDefiance", "挑战头巾");
        ITEM_CN.put("CDOTA_Item_HolyLocket", "圣洁吊坠");
        ITEM_CN.put("CDOTA_Item_ArcaneBoots", "奥术鞋");
        ITEM_CN.put("CDOTA_Item_Dagon", "达贡之神力");
        ITEM_CN.put("CDOTA_Item_Necronomicon", "死灵书");
        ITEM_CN.put("CDOTA_Item_BlackKingBar", "黑皇杖");
        ITEM_CN.put("CDOTA_Item_MantaStyle", "幻影斧");
        ITEM_CN.put("CDOTA_Item_Butterfly", "蝴蝶");
        ITEM_CN.put("CDOTA_Item_Satanic", "撒旦之邪力");
        ITEM_CN.put("CDOTA_Item_Mjollnir", "雷神之锤");
        ITEM_CN.put("CDOTA_Item_Maelstrom", "漩涡");
        ITEM_CN.put("CDOTA_Item_Desolator", "黯灭");
        ITEM_CN.put("CDOTA_Item_MonkeyKingBar", "金箍棒");
        ITEM_CN.put("CDOTA_Item_Daedalus", "代达罗斯之殇");
        ITEM_CN.put("CDOTA_Item_Crystalys", "水晶剑");
        ITEM_CN.put("CDOTA_Item_Armlet", "莫尔迪基安的臂章");
        ITEM_CN.put("CDOTA_Item_Sange", "散华");
        ITEM_CN.put("CDOTA_Item_Yasha", "夜叉");
        ITEM_CN.put("CDOTA_Item_Kaya", "慧光");
        ITEM_CN.put("CDOTA_Item_SangeAndYasha", "散夜对剑");
        ITEM_CN.put("CDOTA_Item_KayaAndSange", "散慧对剑");
        ITEM_CN.put("CDOTA_Item_YashaAndKaya", "慧夜对剑");
        ITEM_CN.put("CDOTA_Item_SilverEdge", "白银之锋");
        ITEM_CN.put("CDOTA_Item_ShadowBlade", "影刃");
        ITEM_CN.put("CDOTA_Item_EtherealBlade", "虚灵之刃");
        ITEM_CN.put("CDOTA_Item_DiffusalBlade", "净魂之刃");
        ITEM_CN.put("CDOTA_Item_HeavensHalberd", "天堂之戟");
        ITEM_CN.put("CDOTA_Item_AbyssalBlade", "深渊之刃");
        ITEM_CN.put("CDOTA_Item_Skadi", "斯嘉蒂之眼");
        ITEM_CN.put("CDOTA_Item_Bloodthorn", "血棘");
        ITEM_CN.put("CDOTA_Item_OrchidMalevolence", "紫怨");
        ITEM_CN.put("CDOTA_Item_RefresherOrb", "刷新球");
        ITEM_CN.put("CDOTA_Item_LinkensSphere", "林肯法球");
        ITEM_CN.put("CDOTA_Item_HurricanePike", "飓风长戟");
        ITEM_CN.put("CDOTA_Item_DragonLance", "魔龙枪");
        ITEM_CN.put("CDOTA_Item_BladeMail", "刃甲");
        ITEM_CN.put("CDOTA_Item_CrimsonGuard", "赤红甲");
        ITEM_CN.put("CDOTA_Item_AssaultCuirass", "强袭胸甲");
        ITEM_CN.put("CDOTA_Item_ShivasGuard", "希瓦的守护");
        ITEM_CN.put("CDOTA_Item_Radiance", "辉耀");
        ITEM_CN.put("CDOTA_Item_HeartOfTarrasque", "恐鳌之心");
        ITEM_CN.put("CDOTA_Item_Vanguard", "先锋盾");
        ITEM_CN.put("CDOTA_Item_SoulBooster", "振魂石");
        ITEM_CN.put("CDOTA_Item_Bloodstone", "血精石");
        ITEM_CN.put("CDOTA_Item_OctarineCore", "玲珑心");
        ITEM_CN.put("CDOTA_Item_EchoSabre", "回音战刃");
        ITEM_CN.put("CDOTA_Item_HandOfMidas", "迈达斯之手");
        ITEM_CN.put("CDOTA_Item_MoonShard", "银月之晶");
        ITEM_CN.put("CDOTA_Item_Reaver", "掠夺者之斧");
        ITEM_CN.put("CDOTA_Item_TalismanOfEvasion", "闪避护符");
        ITEM_CN.put("CDOTA_Item_Hyperstone", "振奋宝石");
        ITEM_CN.put("CDOTA_Item_PointBooster", "精气之球");
        ITEM_CN.put("CDOTA_Item_UltimateScepter", "阿哈利姆神杖");
        ITEM_CN.put("CDOTA_Item_AghanimsShard", "阿哈利姆魔晶");
        ITEM_CN.put("CDOTA_Item_BootsOfSpeed", "速度之靴");
        ITEM_CN.put("CDOTA_Item_Famango", "仙灵果");
        ITEM_CN.put("CDOTA_Item_Ward_Dispenser", "侦查·岗哨守卫");
        ITEM_CN.put("CDOTA_Item_Infused_Raindrop", "凝魂之露");
        ITEM_CN.put("CDOTA_Item_Recipe_MagicWand", "大魔棒卷轴");
        ITEM_CN.put("CDOTA_Item_EmptyBottle", "空瓶");
        ITEM_CN.put("CDOTA_Item_Dagon_Upgraded", "达贡之神力");
        ITEM_CN.put("CDOTA_Item_Spellslinger", "法术棱镜");
        ITEM_CN.put("CDOTA_Item_Enhancement_Keen_Eyed", "锐利之眼");
        ITEM_CN.put("CDOTA_Item_SerratedShiv", "锯齿短刀");
        ITEM_CN.put("CDOTA_Item_Enhancement_Brawny", "壮实身躯");
        ITEM_CN.put("CDOTA_Item_Assault_Cuirass", "强袭胸甲");
        ITEM_CN.put("CDOTA_Item_AssaultCuirass", "强袭胸甲");
        ITEM_CN.put("CDOTA_Item_Enhancement_Crude", "粗糙强化");
        ITEM_CN.put("CDOTA_Item_Spirit_Vessel", "魂之灵瓮");
        ITEM_CN.put("CDOTA_Item_SpiritVessel", "魂之灵瓮");
        ITEM_CN.put("CDOTA_Item_Shivas_Guard", "希瓦的守护");
        ITEM_CN.put("CDOTA_Item_ShivasGuard", "希瓦的守护");
        ITEM_CN.put("CDOTA_Item_Smoke_Of_Deceit", "诡计之雾");
        ITEM_CN.put("CDOTA_Item_SmokeOfDeceit", "诡计之雾");
        ITEM_CN.put("CDOTA_Item_Ward_Dispenser", "侦查·岗哨守卫");
        ITEM_CN.put("CDOTA_Item_Enchanters_Bauble", "巫师坠饰");
        ITEM_CN.put("CDOTA_Item_EnchantersBauble", "巫师坠饰");
        ITEM_CN.put("CDOTA_Item_Octarine_Core", "玲珑心");
        ITEM_CN.put("CDOTA_Item_OctarineCore", "玲珑心");
        ITEM_CN.put("CDOTA_Item_Vladmir", "弗拉迪米尔的祭品");
        ITEM_CN.put("CDOTA_Item_Arcane_Boots", "奥术鞋");
        ITEM_CN.put("CDOTA_Item_ArcaneBoots", "奥术鞋");
        ITEM_CN.put("CDOTA_Item_Dagon", "达贡之神力");
        ITEM_CN.put("CDOTA_Item_Dagon_Upgraded", "达贡之神力");
        ITEM_CN.put("CDOTA_Item_DagonUpgraded", "达贡之神力");
        ITEM_CN.put("CDOTA_Item_Veil_Of_Discord", "纷争面纱");
        ITEM_CN.put("CDOTA_Item_VeilOfDiscord", "纷争面纱");
        ITEM_CN.put("CDOTA_Item_Yasha_And_Kaya", "慧夜对剑");
        ITEM_CN.put("CDOTA_Item_YashaAndKaya", "慧夜对剑");
        ITEM_CN.put("CDOTA_Item_Kaya_And_Sange", "散慧对剑");
        ITEM_CN.put("CDOTA_Item_KayaAndSange", "散慧对剑");
        ITEM_CN.put("CDOTA_Item_Blink_Dagger", "闪烁匕首");
        ITEM_CN.put("CDOTA_Item_Blade_Mail", "刃甲");
        ITEM_CN.put("CDOTA_Item_Black_King_Bar", "黑皇杖");
        ITEM_CN.put("CDOTA_Item_Poor_Mans_Shield", "穷鬼盾");
        ITEM_CN.put("CDOTA_Item_PoorMansShield", "穷鬼盾");
        ITEM_CN.put("CDOTA_Item_Boots_Of_Bearing", "动力鞋");
        ITEM_CN.put("CDOTA_Item_Lotus_Orb", "清莲宝珠");
        ITEM_CN.put("CDOTA_Item_Jidi_Pollen_Bag", "吉迪花粉袋");
        ITEM_CN.put("CDOTA_Item_Cloak_Of_Flames", "火焰斗篷");
        ITEM_CN.put("CDOTA_Item_Conjurers_Catalyst", "召唤者触媒");
        ITEM_CN.put("CDOTA_Item_Consecrated_Wraps", "神圣裹布");
        ITEM_CN.put("CDOTA_Item_Dormant_Curio", "休眠奇物");
        ITEM_CN.put("CDOTA_Item_Enhancement_Quickened", "迅捷强化");
        ITEM_CN.put("CDOTA_Item_Enhancement_Timelss", "永恒强化");
        ITEM_CN.put("CDOTA_Item_Enhancement_Mystical", "神秘强化");
        ITEM_CN.put("CDOTA_Item_Enhancement_Greedy", "贪婪强化");
        ITEM_CN.put("CDOTA_Item_Boots_Of_Bearing", "动力鞋");
    }
    
    static class HeroData {
        int playerId;
        String heroName;
        int team;
        List<float[]> positions = new ArrayList<>();
        List<String> itemEvents = new ArrayList<>();
        Set<String> lastItemSet = new HashSet<>();
        int deathCount = 0;
        int lastHealth = -1;
        boolean isDead = false;
        int lastDeathTick = -1000;
        float lastX = 0;
        float lastY = 0;
    }
    
    static class DeathEvent {
        int tick;
        String heroName;
        int playerId;
        float[] position;
        String killerName;  // May be null if not available
        float gameTime;
    }
    
    // JSON output classes
    static class MatchData {
        int totalTicks;
        List<HeroJson> radiant = new ArrayList<>();
        List<HeroJson> dire = new ArrayList<>();
        List<DeathJson> deaths = new ArrayList<>();
        Map<String, String> steamIdToHero = new HashMap<>();  // steamId (string) -> heroName
    }
    
    static class HeroJson {
        String heroName;
        int playerId;
        int team;
        String lane;
        int deaths;
        List<String> items = new ArrayList<>();
        List<String> itemEvents = new ArrayList<>();
    }
    
    static class DeathJson {
        int tick;
        float gameTimeMinutes;  // Converted from tick
        String heroName;
        String killerName;      // Who killed this hero (if available)
        List<Double> position;  // Use List instead of float[] for Gson serialization
        String location;        // Lane/area description
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.out.println("Usage: java DemParser <dem_file> [steam_id] [output_json]");
            System.exit(1);
        }

        String demFile = args[0];
        String targetSteamId = args.length > 1 ? args[1] : null;
        String outputJson = args.length > 2 ? args[2] : null;
        
        System.out.println("Parsing DEM file: " + demFile);
        
        try {
            MappedFileSource source = new MappedFileSource(demFile);
            DemParser parser = new DemParser();
            new SimpleRunner(source).runWith(parser);
            
            if (outputJson != null) {
                parser.writeJson(outputJson, targetSteamId);
            } else {
                parser.printResults(targetSteamId);
            }
            
        } catch (Exception e) {
            System.err.println("Error parsing DEM file: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    @OnTickEnd
    public void onTickEnd(Context ctx, boolean synthetic) {
        tickCount++;
    }
    
    @OnEntityCreated
    public void onEntityCreated(Context ctx, Entity entity) {
        String name = entity.getDtClass().getDtName();
        
        if (name.startsWith("CDOTA_Item_")) {
            int handle = entity.getHandle();
            itemEntities.put(handle, name);
        }
        
        if (name.startsWith("CDOTA_Unit_Hero_")) {
            int playerId = -1;
            try {
                Object pid = entity.getProperty("m_iPlayerID");
                if (pid != null) playerId = ((Number) pid).intValue();
            } catch (Exception e) {
                playerId = entity.getIndex();
            }
            
            if (playerId >= 0) {
                HeroData hero = heroes.get(playerId);
                if (hero == null) {
                    hero = new HeroData();
                    hero.playerId = playerId;
                    hero.heroName = name.replace("CDOTA_Unit_Hero_", "");
                    heroes.put(playerId, hero);
                }
                
                try {
                    Object team = entity.getProperty("m_iTeamNum");
                    if (team != null) hero.team = ((Number) team).intValue();
                } catch (Exception e) {}
            }
        }
        
        // Capture Steam ID from player controller entities
        if (name.equals("CDOTAPlayerController")) {
            try {
                Object steamId = entity.getProperty("m_steamID");
                Object playerId = entity.getProperty("m_nPlayerID");
                if (steamId != null && playerId != null) {
                    long steam = ((Number) steamId).longValue();
                    int pid = ((Number) playerId).intValue();
                    if (steam != 0) {
                        playerIdToSteamId.put(pid, steam);
                    }
                }
            } catch (Exception e) {}
        }
    }
    
    @OnEntityUpdated
    public void onEntityUpdated(Context ctx, Entity entity, FieldPath[] updatedPaths, int updateCount) {
        String name = entity.getDtClass().getDtName();
        
        if (name.startsWith("CDOTA_Unit_Hero_")) {
            int playerId = -1;
            try {
                Object pid = entity.getProperty("m_iPlayerID");
                if (pid != null) playerId = ((Number) pid).intValue();
            } catch (Exception e) {
                playerId = entity.getIndex();
            }
            
            HeroData hero = heroes.get(playerId);
            if (hero == null) return;
            
            if (tickCount < 36000) {
                try {
                    Object cellX = entity.getProperty("CBodyComponent.m_cellX");
                    Object cellY = entity.getProperty("CBodyComponent.m_cellY");
                    Object vecX = entity.getProperty("CBodyComponent.m_vecX");
                    Object vecY = entity.getProperty("CBodyComponent.m_vecY");
                    
                    if (cellX != null && cellY != null && vecX != null && vecY != null) {
                        float x = ((Number)cellX).floatValue() * 128.0f + ((Number)vecX).floatValue();
                        float y = ((Number)cellY).floatValue() * 128.0f + ((Number)vecY).floatValue();
                        hero.positions.add(new float[]{x, y, tickCount});
                        hero.lastX = x;
                        hero.lastY = y;
                    }
                } catch (Exception e) {}
            }
            
            try {
                Set<String> currentItemSet = new HashSet<>();
                List<String> currentItemList = new ArrayList<>();
                for (int i = 0; i < 25; i++) {
                    String slotName = String.format("m_hItems.%04d", i);
                    Object itemHandle = entity.getProperty(slotName);
                    if (itemHandle != null) {
                        int handle = ((Number) itemHandle).intValue();
                        if (handle != 16777215) {
                            String itemName = itemEntities.get(handle);
                            if (itemName != null) {
                                String cnName = ITEM_CN.getOrDefault(itemName, itemName.replace("CDOTA_Item_", ""));
                                currentItemSet.add(cnName);
                                currentItemList.add(cnName);
                            }
                        }
                    }
                }
                
                if (!currentItemSet.equals(hero.lastItemSet) && !currentItemSet.isEmpty()) {
                    String itemEvent = String.format("[tick:%d] %s", tickCount, String.join(", ", currentItemList));
                    hero.itemEvents.add(itemEvent);
                    hero.lastItemSet = currentItemSet;
                }
            } catch (Exception e) {}
        }
    }
    
    @OnCombatLogEntry
    public void onCombatLogEntry(Context ctx, CombatLogEntry entry) {
        if (entry.getType().toString().equals("DOTA_COMBATLOG_DEATH")) {
            String targetName = entry.getTargetName();
            String attackerName = entry.getAttackerName();
            float timestamp = entry.getTimestamp();
            
            // Only track hero deaths (not creep deaths)
            if (targetName == null || !targetName.startsWith("npc_dota_hero_")) {
                return;
            }
            
            // Convert "npc_dota_hero_windrunner" -> "Windrunner"
            String heroName = targetName.replace("npc_dota_hero_", "");
            heroName = capitalizeFirst(heroName);
            
            // Convert attacker name similarly
            String killerName = null;
            if (attackerName != null && attackerName.startsWith("npc_dota_hero_")) {
                killerName = capitalizeFirst(attackerName.replace("npc_dota_hero_", ""));
            } else if (attackerName != null) {
                killerName = attackerName;
            }
            
            // Find matching hero by name
            HeroData matchedHero = null;
            int matchedPlayerId = -1;
            for (Map.Entry<Integer, HeroData> h : heroes.entrySet()) {
                if (h.getValue().heroName.equalsIgnoreCase(heroName)) {
                    matchedHero = h.getValue();
                    matchedPlayerId = h.getKey();
                    break;
                }
            }
            
            if (matchedHero != null) {
                matchedHero.deathCount++;
            }
            
            // Use hero's last known position from entity tracking (combatlog location is often 0)
            float[] deathPos = new float[]{0.0f, 0.0f};
            if (matchedHero != null && matchedHero.lastX != 0.0f && matchedHero.lastY != 0.0f) {
                deathPos = new float[]{matchedHero.lastX, matchedHero.lastY};
            }
            
            DeathEvent death = new DeathEvent();
            death.tick = tickCount;
            death.heroName = heroName;
            death.playerId = matchedPlayerId;
            death.position = deathPos;
            death.killerName = killerName;
            death.gameTime = timestamp;
            deaths.add(death);
        }
    }
    
    private String capitalizeFirst(String s) {
        if (s == null || s.isEmpty()) return s;
        return Character.toUpperCase(s.charAt(0)) + s.substring(1);
    }
    
    private float tickToGameTime(int tick) {
        // Dota2 runs at 30 ticks per second, game time starts at 0
        return tick / 30.0f / 60.0f;
    }
    
    private String determineLocation(float[] position, int team) {
        if (position == null || position.length < 2) return "未知";
        float x = position[0];
        float y = position[1];
        
        // Dota2 map coordinates:
        // (0,0) = bottom-left (天辉基地)
        // (25000, 25000) = top-right (夜魇基地)
        // Top lane = high Y (toward top-right)
        // Bot lane = low Y (toward bottom-left)
        // Mid lane = diagonal
        // Note: y > 15000 is actually 上路 (top), y < 7000 is 下路 (bottom)
        // This is the same for both teams since it's absolute map position
        
        // Check if in base
        if (x < 4000 && y < 4000) return "天辉基地";
        if (x > 20000 && y > 20000) return "夜魇基地";
        
        // Check lanes by absolute position (not team-relative)
        // 上路 (Top): y > 15000 (upper part of map)
        // 下路 (Bot): y < 7000 (lower part of map)
        // 中路 (Mid): between 7000 and 15000
        if (y > 15000) return "上路";
        if (y < 7000) return "下路";
        return "中路/河道";
    }
    
    private void writeJson(String outputPath, String targetSteamId) throws IOException {
        MatchData match = new MatchData();
        match.totalTicks = tickCount;
        
        for (HeroData hero : heroes.values()) {
            HeroJson hj = new HeroJson();
            hj.heroName = hero.heroName;
            hj.playerId = hero.playerId;
            hj.team = hero.team;
            hj.deaths = hero.deathCount;
            
            if (!hero.positions.isEmpty()) {
                float avgX = 0, avgY = 0;
                for (float[] pos : hero.positions) {
                    avgX += pos[0];
                    avgY += pos[1];
                }
                avgX /= hero.positions.size();
                avgY /= hero.positions.size();
                hj.lane = determineLane(avgX, avgY, hero.team);
            }
            
            // Get final items (last item event)
            if (!hero.itemEvents.isEmpty()) {
                String lastEvent = hero.itemEvents.get(hero.itemEvents.size() - 1);
                String itemsStr = lastEvent.substring(lastEvent.indexOf("]") + 2);
                hj.items = Arrays.asList(itemsStr.split(", "));
                // Add all item events for timeline analysis
                hj.itemEvents = new ArrayList<>(hero.itemEvents);
            }
            
            if (hero.team == 2) match.radiant.add(hj);
            else match.dire.add(hj);
        }
        
        for (DeathEvent death : deaths) {
            DeathJson dj = new DeathJson();
            dj.tick = death.tick;
            dj.gameTimeMinutes = death.gameTime / 60.0f;
            dj.heroName = death.heroName;
            dj.killerName = death.killerName;
            dj.position = Arrays.asList((double)death.position[0], (double)death.position[1]);
            dj.location = determineLocation(death.position, 
                heroes.get(death.playerId) != null ? heroes.get(death.playerId).team : 0);
            match.deaths.add(dj);
        }
        
        // Build steamId -> heroName mapping
        for (Map.Entry<Integer, Long> entry : playerIdToSteamId.entrySet()) {
            int pid = entry.getKey();
            long steamId = entry.getValue();
            HeroData hero = heroes.get(pid);
            if (hero != null) {
                match.steamIdToHero.put(String.valueOf(steamId), hero.heroName);
            }
        }
        
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        try (FileWriter writer = new FileWriter(outputPath)) {
            gson.toJson(match, writer);
        }
        System.out.println("JSON output written to: " + outputPath);
    }
    
    private void printResults(String targetSteamId) {
        System.out.println("\n=== Parsing Results ===");
        System.out.println("Total ticks: " + tickCount);
        System.out.println("Heroes found: " + heroes.size());
        System.out.println("Deaths found: " + deaths.size());
        
        System.out.println("\n=== Teams ===");
        List<String> radiant = new ArrayList<>();
        List<String> dire = new ArrayList<>();
        for (HeroData hero : heroes.values()) {
            if (hero.team == 2) radiant.add(hero.heroName);
            else if (hero.team == 3) dire.add(hero.heroName);
            else radiant.add(hero.heroName + "(?)");
        }
        System.out.println("Radiant (天辉): " + String.join(", ", radiant));
        System.out.println("Dire (夜魇): " + String.join(", ", dire));
        
        System.out.println("\n=== Hero Positions Summary (first 10 min) ===");
        for (HeroData hero : heroes.values()) {
            if (!hero.positions.isEmpty()) {
                float avgX = 0, avgY = 0;
                for (float[] pos : hero.positions) {
                    avgX += pos[0];
                    avgY += pos[1];
                }
                avgX /= hero.positions.size();
                avgY /= hero.positions.size();
                String lane = determineLane(avgX, avgY, hero.team);
                System.out.println(hero.heroName + ": avg pos=[" + String.format("%.1f", avgX) + ", " + String.format("%.1f", avgY) + "], lane=" + lane + ", samples=" + hero.positions.size());
            }
        }
        
        System.out.println("\n=== Death Events (first 30) ===");
        for (int i = 0; i < Math.min(30, deaths.size()); i++) {
            DeathEvent death = deaths.get(i);
            String posStr = death.position != null ? " pos=[" + String.format("%.1f", death.position[0]) + ", " + String.format("%.1f", death.position[1]) + "]" : "";
            String killerStr = death.killerName != null ? " killed by " + death.killerName : "";
            String timeStr = String.format("[%.1f min]", death.gameTime / 60.0f);
            System.out.println(timeStr + " " + death.heroName + " died" + killerStr + posStr);
        }
        if (deaths.size() > 30) {
            System.out.println("... and " + (deaths.size() - 30) + " more deaths");
        }
        
        System.out.println("\n=== Hero Item Changes (first 15 per hero) ===");
        for (HeroData hero : heroes.values()) {
            if (!hero.itemEvents.isEmpty()) {
                System.out.println("\n" + hero.heroName + " (deaths=" + hero.deathCount + "):");
                for (int i = 0; i < Math.min(15, hero.itemEvents.size()); i++) {
                    System.out.println("  " + hero.itemEvents.get(i));
                }
                if (hero.itemEvents.size() > 15) {
                    System.out.println("  ... and " + (hero.itemEvents.size() - 15) + " more changes");
                }
            }
        }
    }
    
    private String determineLane(float x, float y, int team) {
        if (team == 2) {
            if (y > 15000) return "上路 (Top)";
            if (y < 7000) return "下路 (Bot)";
            return "中路 (Mid)";
        } else {
            if (y < 7000) return "上路 (Top)";
            if (y > 15000) return "下路 (Bot)";
            return "中路 (Mid)";
        }
    }
}
