# -*- coding: utf-8 -*-
from __future__ import division
import re

import maya.cmds as cmds
import maya.mel as mel


class FbxToHIK:

    # ====================================================================
    #  HumanIK 骨骼 ID 映射（HIK 内部索引 → 骨骼类型名）
    #  参考 Maya HumanIK 文档中 setCharacterObject 的索引定义
    # ====================================================================

    # 核心骨骼 ID
    HIK_ID = {
        "Reference":      0,
        "Hips":           1,
        "LeftUpLeg":      2,
        "LeftLeg":        3,
        "LeftFoot":       4,
        "RightUpLeg":     5,
        "RightLeg":       6,
        "RightFoot":      7,
        "Spine":          8,
        "LeftArm":        9,
        "LeftForeArm":   10,
        "LeftHand":      11,
        "RightArm":      12,
        "RightForeArm":  13,
        "RightHand":     14,
        "Head":          15,
        "LeftToeBase":   16,
        "RightToeBase":  17,
        "LeftShoulder":  18,
        "RightShoulder": 19,
        "Neck":          20,
        "LeftFingerBase":  21,
        "RightFingerBase": 22,
        # 额外脊柱
        "Spine1":  23,
        "Spine2":  24,
        "Spine3":  25,
        "Spine4":  26,
        "Spine5":  27,
        "Spine6":  28,
        "Spine7":  29,
        "Spine8":  30,
        "Spine9":  31,
        # 额外颈部
        "Neck1":   32,
        "Neck2":   33,
        "Neck3":   34,
        "Neck4":   35,
        "Neck5":   36,
        "Neck6":   37,
        "Neck7":   38,
        "Neck8":   39,
        "Neck9":   40,
        # 左手手指
        "LeftHandThumb1":  50,
        "LeftHandThumb2":  51,
        "LeftHandThumb3":  52,
        "LeftHandThumb4":  53,
        "LeftHandIndex1":  54,
        "LeftHandIndex2":  55,
        "LeftHandIndex3":  56,
        "LeftHandIndex4":  57,
        "LeftHandMiddle1": 58,
        "LeftHandMiddle2": 59,
        "LeftHandMiddle3": 60,
        "LeftHandMiddle4": 61,
        "LeftHandRing1":   62,
        "LeftHandRing2":   63,
        "LeftHandRing3":   64,
        "LeftHandRing4":   65,
        "LeftHandPinky1":  66,
        "LeftHandPinky2":  67,
        "LeftHandPinky3":  68,
        "LeftHandPinky4":  69,
        # 右手手指
        "RightHandThumb1":  74,
        "RightHandThumb2":  75,
        "RightHandThumb3":  76,
        "RightHandThumb4":  77,
        "RightHandIndex1":  78,
        "RightHandIndex2":  79,
        "RightHandIndex3":  80,
        "RightHandIndex4":  81,
        "RightHandMiddle1": 82,
        "RightHandMiddle2": 83,
        "RightHandMiddle3": 84,
        "RightHandMiddle4": 85,
        "RightHandRing1":   86,
        "RightHandRing2":   87,
        "RightHandRing3":   88,
        "RightHandRing4":   89,
        "RightHandPinky1":  90,
        "RightHandPinky2":  91,
        "RightHandPinky3":  92,
        "RightHandPinky4":  93,
        # Roll 骨骼（twist bones）
        "LeftUpLegRoll":     41,
        "LeftLegRoll":       42,
        "RightUpLegRoll":    43,
        "RightLegRoll":      44,
        "LeftArmRoll":       45,
        "LeftForeArmRoll":   46,
        "RightArmRoll":      47,
        "RightForeArmRoll":  48,
    }

    # UE 骨骼名称 → HIK 骨骼类型名 的静态映射（主体骨骼）
    # 脊柱/颈部/手指需要动态检测
    UE_TO_HIK_BODY = {
        "root":        "Reference",
        "pelvis":      "Hips",
        "thigh_l":     "LeftUpLeg",
        "calf_l":      "LeftLeg",
        "foot_l":      "LeftFoot",
        "thigh_r":     "RightUpLeg",
        "calf_r":      "RightLeg",
        "foot_r":      "RightFoot",
        "clavicle_l":  "LeftShoulder",
        "upperarm_l":  "LeftArm",
        "lowerarm_l":  "LeftForeArm",
        "hand_l":      "LeftHand",
        "clavicle_r":  "RightShoulder",
        "upperarm_r":  "RightArm",
        "lowerarm_r":  "RightForeArm",
        "hand_r":      "RightHand",
    }

    # 手指前缀 → HIK 左/右手指名称模板
    FINGER_PREFIXES = [
        ("thumb",  "Thumb"),
        ("index",  "Index"),
        ("middle", "Middle"),
        ("ring",   "Ring"),
        ("pinky",  "Pinky"),
    ]

    # ====================================================================
    #  构造
    # ====================================================================

    def __init__(self, character_name="Character1"):
        """
        Args:
            character_name: HIK Character 节点名称。
        """
        self.character_name = character_name

    # ====================================================================
    #  静态工具方法
    # ====================================================================

    @staticmethod
    def _joint_basename(joint_name):
        """返回 DAG 全路径中最后一段（短名）。"""
        return joint_name.split("|")[-1]

    @staticmethod
    def _natural_sort_key(joint_name):
        """自然排序键：按字母 + 数值混合排序 joint 名称。"""
        name = joint_name.split("|")[-1].lower()
        parts = re.split(r"(\d+)", name)
        return [int(p) if p.isdigit() else p for p in parts]

    # ====================================================================
    #  骨骼查询（复用 FbxToAdv 的逻辑）
    # ====================================================================

    def _get_descendant_joints(self, root_joint, prefix):
        """获取 root_joint 下所有以 prefix 开头的 joint，按自然排序返回。"""
        if not cmds.objExists(root_joint):
            raise RuntimeError("场景中没有找到对象: {0}".format(root_joint))

        descendants = (
            cmds.listRelatives(root_joint, ad=True, type="joint", fullPath=True) or []
        )
        matched = [
            j for j in descendants
            if self._joint_basename(j).lower().startswith(prefix.lower())
        ]
        matched.sort(key=self._natural_sort_key)

        if not matched:
            raise RuntimeError(
                "在 {0} 的子级中没有找到以 '{1}' 开头的 joint".format(root_joint, prefix)
            )
        return matched

    def _get_nearest_level_joint(self, root_joint, prefix):
        """从 root_joint 往下逐层查找，返回最近层级中第一个匹配 prefix 的 joint。"""
        if not cmds.objExists(root_joint):
            raise RuntimeError("场景中没有找到对象: {0}".format(root_joint))

        current_level = (
            cmds.listRelatives(root_joint, c=True, type="joint", fullPath=True) or []
        )
        prefix_lower = prefix.lower()

        while current_level:
            matched = [
                j for j in current_level
                if self._joint_basename(j).lower().startswith(prefix_lower)
            ]
            matched.sort(key=self._natural_sort_key)
            if matched:
                return matched[0]

            next_level = []
            for joint in current_level:
                next_level.extend(
                    cmds.listRelatives(joint, c=True, type="joint", fullPath=True)
                    or []
                )
            current_level = next_level

        raise RuntimeError(
            "在 {0} 的后代层级中没有找到以 '{1}' 开头的 joint".format(root_joint, prefix)
        )

    def _find_scene_joints_by_prefix(self, prefix):
        """从全场景按名称前缀查找 joint，不依赖层级。"""
        prefix_lower = prefix.lower()
        joints = []
        for joint in cmds.ls(type="joint", long=True) or []:
            name = self._joint_basename(joint).split(":")[-1].lower()
            if name.startswith(prefix_lower):
                joints.append(joint)
        joints.sort(key=self._natural_sort_key)
        return joints

    def _get_neck_source_from_spine(self):
        """直接从场景查找 neck joint。"""
        neck_joints = self._find_scene_joints_by_prefix("neck")
        if neck_joints:
            return neck_joints[0]
        raise RuntimeError("场景中没有找到 neck joint")

    def _get_head_source(self):
        """直接从场景查找 head joint。"""
        head_joints = self._find_scene_joints_by_prefix("head")
        if head_joints:
            return head_joints[0]
        raise RuntimeError("场景中没有找到 head joint")

    def _build_neck_chain(self):
        """直接返回场景中的 neck 链。"""
        return [self._joint_basename(j) for j in self._find_scene_joints_by_prefix("neck")]

    def _get_toe_joint(self, foot_name):
        """获取 foot 下的第一个子 joint（脚趾）。"""
        children = (
            cmds.listRelatives(foot_name, c=True, type="joint", fullPath=True) or []
        )
        if children:
            return self._joint_basename(children[0])
        return None

    def _find_calf_name(self, thigh_name):
        """优先按 calf 名称找小腿，避免辅助骨覆盖 HIK Leg。"""
        side = "_l" if thigh_name.endswith("_l") else "_r" if thigh_name.endswith("_r") else ""
        standard_name = "calf{0}".format(side) if side else ""
        if standard_name and cmds.objExists(standard_name):
            return standard_name
        if not cmds.objExists(thigh_name):
            return None

        def _is_calf_joint(joint):
            name = self._joint_basename(joint).split(":")[-1].lower()
            if any(token in name for token in ("twist", "corrective", "real", "bibone", "bone_g")):
                return False
            if not name.startswith("calf"):
                return False
            return not side or name.endswith(side)

        children = cmds.listRelatives(thigh_name, c=True, type="joint", fullPath=True) or []
        candidates = [j for j in children if _is_calf_joint(j)]
        if not candidates:
            descendants = cmds.listRelatives(thigh_name, ad=True, type="joint", fullPath=True) or []
            candidates = [j for j in descendants if _is_calf_joint(j)]
        if not candidates:
            return None
        candidates.sort(key=self._natural_sort_key)
        return candidates[0]

    # ====================================================================
    #  手指检测
    # ====================================================================

    def _get_finger_joints(self, hand_name, prefix, max_count=4):
        """获取 hand_name 下以 prefix 开头的手指 joint 链（最多 max_count 个）。"""
        try:
            joints = self._get_descendant_joints(hand_name, prefix)
            return joints[:max_count]
        except RuntimeError:
            return []

    # ====================================================================
    #  HIK 插件加载
    # ====================================================================

    @staticmethod
    def _ensure_hik_loaded():
        """确保 HumanIK 插件已加载。"""
        if not cmds.pluginInfo("mayaHIK", q=True, loaded=True):
            cmds.loadPlugin("mayaHIK")

        # source HIK MEL 脚本
        try:
            mel.eval("HIKCharacterControlsTool;")
        except Exception:
            pass

    # ====================================================================
    #  HIK 角色创建
    # ====================================================================

    def _create_character(self):
        """创建 HIK Character 节点。"""
        mel.eval('hikCreateCharacter("{0}")'.format(self.character_name))

    def _set_character_object(self, joint_name, hik_bone_name):
        """将 joint 映射到 HIK Character 的指定骨骼槽位。

        Args:
            joint_name: 场景中的 joint 名称。
            hik_bone_name: HIK 骨骼类型名称，如 "Hips", "LeftUpLeg" 等。
        """
        hik_id = self.HIK_ID.get(hik_bone_name)
        if hik_id is None:
            cmds.warning("未知的 HIK 骨骼类型: {0}，跳过 {1}".format(hik_bone_name, joint_name))
            return

        if not cmds.objExists(joint_name):
            cmds.warning("Joint {0} 不存在，跳过 HIK 映射".format(joint_name))
            return

        mel.eval(
            'setCharacterObject("{0}", "{1}", {2}, 0)'.format(joint_name, self.character_name, hik_id)
        )

    def _lock_definition(self):
        """锁定 HIK 角色定义。"""
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        mel.eval("hikToggleLockDefinition")

    def _create_control_rig(self):
        """为 HIK 角色创建控制绑定。"""
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        mel.eval("hikCreateControlRig")

    # ====================================================================
    #  更新 HIK UI（确保状态同步）
    # ====================================================================

    @staticmethod
    def _update_hik_ui():
        """更新 HIK 工具 UI 状态。"""
        try:
            mel.eval("""
                if (`exists hikUpdateCharacterList`)
                {
                    hikUpdateCharacterList();
                    hikUpdateCurrentCharacterFromUI();
                    hikUpdateContextualUI();
                    hikControlRigSelectionChangedCallback;
                }
            """)
        except Exception:
            pass

    # ====================================================================
    #  设置 Rig Look
    # ====================================================================

    def _set_rig_look_stick(self):
        """将 HIK 控制绑定的显示模式设置为 Stick。"""
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        try:
            # 0=Wire, 1=Stick, 2=Box
            mel.eval('hikSetRigLookAndFeel("{0}", 1)'.format(self.character_name))
        except Exception:
            cmds.warning("无法设置 Rig Look 为 Stick，请手动设置")
        self._update_hik_ui()

    # ====================================================================
    #  主体骨骼映射
    # ====================================================================

    def _map_body_bones(self):
        """映射主体骨骼（不含脊柱/颈部/手指/脚趾）。"""
        for ue_name, hik_name in self.UE_TO_HIK_BODY.items():
            if cmds.objExists(ue_name):
                self._set_character_object(ue_name, hik_name)

        # 标准 calf 已存在时不再动态覆盖；仅缺标准名时按 calf 名称兜底
        for thigh, standard_calf, hik_calf in [
            ("thigh_l", "calf_l", "LeftLeg"),
            ("thigh_r", "calf_r", "RightLeg"),
        ]:
            if cmds.objExists(standard_calf):
                continue
            calf = self._find_calf_name(thigh)
            if calf:
                self._set_character_object(self._joint_basename(calf), hik_calf)

    # ====================================================================
    #  脊柱映射
    # ====================================================================

    def _map_spine(self):
        """动态检测并映射脊柱骨骼链。

        HIK 脊柱定义：
            Spine  (ID 8)  = 第一节脊柱
            Spine1 (ID 23) = 第二节
            Spine2 (ID 24) = 第三节
            ...以此类推
        """
        spine_joints = self._find_scene_joints_by_prefix("spine")
        if not spine_joints:
            cmds.warning("未找到脊柱骨骼，跳过脊柱映射")
            return

        spine_hik_names = ["Spine"] + ["Spine{0}".format(i) for i in range(1, 10)]

        for i, spine_joint in enumerate(spine_joints):
            if i >= len(spine_hik_names):
                break
            joint_short = self._joint_basename(spine_joint)
            self._set_character_object(joint_short, spine_hik_names[i])

    # ====================================================================
    #  颈部映射
    # ====================================================================

    def _map_neck(self):
        """动态检测并映射颈部骨骼链。

        HIK 颈部定义：
            Neck  (ID 20) = 第一节颈部
            Neck1 (ID 32) = 第二节
            ...以此类推
        """
        neck_chain = self._find_scene_joints_by_prefix("neck")
        if not neck_chain:
            cmds.warning("未找到颈部骨骼，跳过颈部映射")
        else:
            neck_hik_names = ["Neck"] + ["Neck{0}".format(i) for i in range(1, 10)]
            for i, joint_name in enumerate(neck_chain):
                if i >= len(neck_hik_names):
                    break
                self._set_character_object(self._joint_basename(joint_name), neck_hik_names[i])

        head_joints = self._find_scene_joints_by_prefix("head")
        if head_joints:
            self._set_character_object(self._joint_basename(head_joints[0]), "Head")
        else:
            cmds.warning("未找到头部骨骼，跳过 Head 映射")

    # ====================================================================
    #  脚趾映射
    # ====================================================================

    def _map_toes(self):
        """映射脚趾骨骼。"""
        for foot, hik_toe in [("foot_l", "LeftToeBase"), ("foot_r", "RightToeBase")]:
            toe = self._get_toe_joint(foot)
            if toe:
                self._set_character_object(toe, hik_toe)

    # ====================================================================
    #  手指映射
    # ====================================================================

    def _map_fingers(self):
        """动态检测并映射双手手指骨骼。

        针对每只手的每根手指，从 hand 骨骼下搜索对应前缀的 joint 链，
        然后按顺序映射到 HIK 手指槽位。
        """
        for hand_name, side_prefix in [("hand_l", "Left"), ("hand_r", "Right")]:
            if not cmds.objExists(hand_name):
                continue

            for ue_prefix, hik_finger in self.FINGER_PREFIXES:
                finger_joints = self._get_finger_joints(hand_name, ue_prefix, max_count=4)

                for j, fj in enumerate(finger_joints):
                    fj_short = self._joint_basename(fj)
                    hik_name = "{0}Hand{1}{2}".format(side_prefix, hik_finger, j + 1)
                    self._set_character_object(fj_short, hik_name)

    # ====================================================================
    #  Roll/Twist 骨骼映射
    # ====================================================================

    def _map_roll_bones(self):
        """检测并映射 twist/roll 骨骼。

        UE 的 twist 骨骼命名模式：
            upperarm_twist_01_l, lowerarm_twist_01_l, thigh_twist_01_l, calf_twist_01_l
        """
        roll_mapping = [
            ("upperarm_l",  "upperarm_twist", "l", "LeftArmRoll"),
            ("lowerarm_l",  "lowerarm_twist", "l", "LeftForeArmRoll"),
            ("thigh_l",     "thigh_twist",    "l", "LeftUpLegRoll"),
            ("calf_l",      "calf_twist",     "l", "LeftLegRoll"),
            ("upperarm_r",  "upperarm_twist", "r", "RightArmRoll"),
            ("lowerarm_r",  "lowerarm_twist", "r", "RightForeArmRoll"),
            ("thigh_r",     "thigh_twist",    "r", "RightUpLegRoll"),
            ("calf_r",      "calf_twist",     "r", "RightLegRoll"),
        ]

        for parent_bone, twist_prefix, side, hik_name in roll_mapping:
            if not cmds.objExists(parent_bone):
                continue
            children = cmds.listRelatives(parent_bone, c=True, type="joint") or []
            for child in children:
                child_lower = child.lower()
                if "twist" in child_lower and side in child_lower:
                    self._set_character_object(child, hik_name)
                    break

    # ====================================================================
    #  公开 API
    # ====================================================================

    def build(self):
        """一键构建 HumanIK 控制绑定。

        流程：
            1. 加载 HumanIK 插件
            2. 创建 HIK Character
            3. 映射所有骨骼到 HIK 定义
            4. 锁定角色定义
            5. 创建控制绑定
        """
        cmds.currentUnit(linear="cm")

        # 将可能存在的 Root 骨骼重命名为 root
        if cmds.objExists("Root") and not cmds.objExists("root"):
            try:
                cmds.rename("Root", "root")
            except Exception:
                pass

        # 1. 加载 HIK
        self._ensure_hik_loaded()

        # 2. 如果已存在同名 Character，先删除
        if cmds.objExists(self.character_name):
            self.delete_controller()

        # 3. 创建 HIK Character
        self._create_character()
        mel.eval('hikSetCurrentCharacter("{0}")'.format(self.character_name))
        self._update_hik_ui()

        # 4. 映射骨骼
        self._map_body_bones()
        self._map_spine()
        self._map_neck()
        self._map_toes()
        self._map_fingers()
        self._map_roll_bones()

        # 5. 锁定定义
        self._lock_definition()
        self._update_hik_ui()

        # 6. 创建控制绑定
        self._create_control_rig()
        self._update_hik_ui()

        # 7. 将 Rig Look 设置为 Stick
        self._set_rig_look_stick()

        cmds.select(clear=True)

    def delete_controller(self):
        """删除 HumanIK 控制器和角色节点。"""
        self._ensure_hik_loaded()
        character = self.character_name if cmds.objExists(self.character_name) else ""
        if not character:
            try:
                characters = mel.eval("hikGetSceneCharacters()") or []
            except Exception:
                characters = []
            if characters:
                character = characters[0]
        if not character:
            cmds.select(clear=True)
            return

        try:
            mel.eval('hikSetCurrentCharacter("{0}")'.format(character))
            self._update_hik_ui()
        except Exception:
            pass

        try:
            control_rig = mel.eval('hikGetControlRig("{0}")'.format(character))
        except Exception:
            control_rig = ""
        if control_rig:
            try:
                mel.eval("hikDeleteControlRig()")
            except Exception:
                if cmds.objExists(control_rig):
                    cmds.delete(control_rig)

        try:
            mel.eval('hikDeleteCharacter("{0}")'.format(character))
        except Exception:
            if cmds.objExists(character):
                cmds.delete(character)

        cmds.select(clear=True)


if __name__ == "__main__":
    FbxToHIK().build()
