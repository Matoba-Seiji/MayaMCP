# -*- coding: utf-8 -*-
from __future__ import division
import io
import os
import re

import maya.cmds as cmds
import maya.mel as mel


class FbxToADV:
    ADV_VERSIONS = (
        ("AdvancedSkeleton",  "AdvancedSkeleton.mel",  "AdvancedSkeletonFiles",  "as"),
        ("AdvancedSkeleton5", "AdvancedSkeleton5.mel", "AdvancedSkeleton5Files", "as"),
    )

    FIT_SKELETON_REL_PARTS = ("fitSkeletons", "biped.ma")

    # 主体对位分两阶段，确保父级先就位
    BODY_POSITION_MAP_PHASE1 = [
        ("Root",     "pelvis"),
        ("Hip",      "thigh_r"),
        ("Knee",     "calf_r"),
        ("Ankle",    "foot_r"),
        ("Spine1",   "spine_01"),
    ]

    BODY_POSITION_MAP_PHASE2 = [
        ("Scapula",  "clavicle_r"),
        ("Shoulder", "upperarm_r"),
        ("Elbow",    "lowerarm_r"),
        ("Wrist",    "hand_r"),
    ]

    # FitSkeleton 节点 → 源骨骼前缀
    TWIST_JOINT_MAP = [
        ("Hip",      "thigh"),
        ("Knee",     "calf"),
        ("Shoulder", "upperarm"),
        ("Elbow",    "lowerarm"),
    ]

    # FitSkeleton 手指链 → 源手指前缀
    FINGER_MAP = [
        (["ThumbFinger1",  "ThumbFinger2",  "ThumbFinger3",  "ThumbFinger4"],  "thumb"),
        (["IndexFinger1",  "IndexFinger2",  "IndexFinger3",  "IndexFinger4"],  "index"),
        (["MiddleFinger1", "MiddleFinger2", "MiddleFinger3", "MiddleFinger4"], "middle"),
        (["RingFinger1",   "RingFinger2",   "RingFinger3",   "RingFinger4"],   "ring"),
        (["PinkyFinger1",  "PinkyFinger2",  "PinkyFinger3",  "PinkyFinger4"],  "pinky"),
    ]

    HAND_SOURCE = "hand_r"
    SHOULDER_HEIGHT_RATIO_REF = 0.235

    TWIST_SEGMENT_END_MAP = {
        "thigh": "calf",
        "calf": "foot",
        "upperarm": "lowerarm",
        "lowerarm": "hand",
    }

    def __init__(self, fit_file=None):
        """初始化 AdvancedSkeleton 路径。"""
        base, version_info = self._find_advancedskeleton_base()
        self.advancedskeleton_base = base
        self._adv_mel_name = version_info[1]
        self._adv_files_dirname = version_info[2]
        self._adv_mel_prefix = version_info[3]

        self._is_z_up = (cmds.upAxis(q=True, ax=True) == "z")

        default_fit_file = os.path.join(
            self.advancedskeleton_base,
            self._adv_files_dirname,
            *self.FIT_SKELETON_REL_PARTS
        )
        self.fit_file = self._normalize_path(fit_file or default_fit_file)

    def _get_height(self, pos):
        """从世界空间坐标中取出高度分量，Z-up 取 [2]，Y-up 取 [1]。"""
        return pos[2] if self._is_z_up else pos[1]

    def _zero_center_axis(self, pos):
        """中心线骨骼侧向归零。"""
        pos = list(pos)
        pos[0] = 0.0
        return pos

    def _mel_cmd(self, proc_suffix):
        """执行当前 ADV 版本的 MEL 过程。"""
        full_name = "{0}{1}".format(self._adv_mel_prefix, proc_suffix)
        mel.eval("{0};".format(full_name))

    def _mel_cmd_if_exists(self, proc_suffix):
        """仅在 proc 已注册时执行；缺失则 warning 跳过（兼容老版本 ADV）。"""
        full_name = "{0}{1}".format(self._adv_mel_prefix, proc_suffix)
        try:
            registered = int(mel.eval('exists "{0}";'.format(full_name)))
        except Exception:
            registered = 0
        if not registered:
            cmds.warning(
                "AdvancedSkeleton proc '{0}' not found, skipped (older ADV version).".format(full_name)
            )
            return False
        mel.eval("{0};".format(full_name))
        return True

    @staticmethod
    def _joint_basename(joint_name):
        """返回 DAG 全路径中最后一段（短名）。"""
        return joint_name.split("|")[-1]

    @staticmethod
    def _natural_sort_key(joint_name):
        """自然排序键：按字母 + 数值混合排序 joint 名称。"""
        name = FbxToADV._joint_basename(joint_name).lower()
        parts = re.split(r"(\d+)", name)
        return [int(p) if p.isdigit() else p for p in parts]

    @staticmethod
    def _distance(pos_a, pos_b):
        """返回两个世界空间坐标之间的欧几里得距离。"""
        return sum((a - b) ** 2 for a, b in zip(pos_a, pos_b)) ** 0.5

    @staticmethod
    def _midpoint(pos_a, pos_b):
        """返回两个世界空间坐标的中点。"""
        return [(a + b) / 2 for a, b in zip(pos_a, pos_b)]

    @staticmethod
    def _set_uniform_scale(node, value):
        """统一设置节点的 XYZ 缩放。"""
        for axis in ("scaleX", "scaleY", "scaleZ"):
            cmds.setAttr("{0}.{1}".format(node, axis), value)

    @staticmethod
    def _safe_set_attr(node, attr, value):
        """仅当属性存在时才设置值。"""
        if cmds.attributeQuery(attr, node=node, exists=True):
            cmds.setAttr("{0}.{1}".format(node, attr), value)

    @staticmethod
    def _safe_parent(child, parent):
        """仅当 child 尚不是 parent 的直接子级时才执行 parent 操作。"""
        current_parents = cmds.listRelatives(child, parent=True) or []
        if current_parents and current_parents[0] == parent:
            return
        cmds.parent(child, parent)

    @staticmethod
    def _normalize_path(path):
        """规范化路径并统一使用正斜杠。"""
        return os.path.normpath(path).replace("\\", "/")

    @classmethod
    def _is_valid_advancedskeleton_base(cls, base_path):
        """校验 AdvancedSkeleton 安装目录。"""
        if not base_path:
            return None

        for version_info in cls.ADV_VERSIONS:
            _dirname, mel_name, files_dirname, _prefix = version_info
            mel_file = os.path.join(base_path, mel_name)
            fit_file = os.path.join(
                base_path, files_dirname, *cls.FIT_SKELETON_REL_PARTS
            )
            if os.path.isfile(mel_file) and os.path.isfile(fit_file):
                return version_info
        return None

    @classmethod
    def _extract_adv_paths_from_shelves(cls):
        """从 Shelf 配置中提取 AdvancedSkeleton 目录。"""
        # 匹配 source "...AdvancedSkeleton.mel" 或 source "...AdvancedSkeleton5.mel"
        pattern = re.compile(
            r'source\s+"([^"]+[/\\]AdvancedSkeleton5?\.mel)"', re.IGNORECASE
        )
        results = []
        seen = set()

        def _add_from_text(text):
            for match in pattern.finditer(text):
                mel_path = match.group(1).replace("\\", "/")
                adv_dir = "/".join(mel_path.split("/")[:-1])
                key = os.path.normpath(adv_dir).lower()
                if key not in seen:
                    seen.add(key)
                    results.append(os.path.normpath(adv_dir))
        # 方式 1：遍历所有 Shelf Tab，逐个激活以强制加载按钮后查询
        # Maya 对未激活的 Shelf Tab 不会创建子控件，需要先切换过去才能读到按钮
        try:
            top_shelf = mel.eval("$tmpVar=$gShelfTopLevel")
            if top_shelf and cmds.layout(top_shelf, exists=True):
                shelf_names = cmds.tabLayout(top_shelf, query=True, childArray=True) or []
                # 记住当前激活的 Tab，查完后恢复
                original_tab = cmds.tabLayout(top_shelf, query=True, selectTab=True) or ""

                for shelf_name in shelf_names:
                    shelf_full = "{0}|{1}".format(top_shelf, shelf_name)
                    if not cmds.shelfLayout(shelf_full, exists=True):
                        continue

                    # 切换到该 Tab，强制 Maya 加载其按钮控件
                    try:
                        cmds.tabLayout(top_shelf, edit=True, selectTab=shelf_name)
                    except Exception:
                        pass

                    buttons = (
                        cmds.shelfLayout(shelf_full, query=True, childArray=True) or []
                    )
                    for btn in buttons:
                        btn_full = "{0}|{1}".format(shelf_full, btn)
                        if not cmds.shelfButton(btn_full, exists=True):
                            continue
                        try:
                            cmd_str = cmds.shelfButton(btn_full, query=True, command=True) or ""
                        except Exception:
                            continue
                        _add_from_text(cmd_str)

                # 恢复原来激活的 Tab
                if original_tab:
                    try:
                        cmds.tabLayout(top_shelf, edit=True, selectTab=original_tab)
                    except Exception:
                        pass
        except Exception:
            pass
        # 方式 2：直接读取磁盘上的 shelf .mel 文件（后备）
        try:
            shelf_dirs = []
            user_app_dir = cmds.internalVar(userAppDir=True) or ""
            if user_app_dir:
                maya_version = cmds.about(version=True) or ""
                if maya_version:
                    shelf_dirs.append(
                        os.path.join(user_app_dir, maya_version, "prefs", "shelves")
                    )
                shelf_dirs.append(os.path.join(user_app_dir, "prefs", "shelves"))

            for shelf_dir in shelf_dirs:
                if not os.path.isdir(shelf_dir):
                    continue
                for fname in os.listdir(shelf_dir):
                    if not fname.lower().endswith(".mel"):
                        continue
                    fpath = os.path.join(shelf_dir, fname)
                    try:
                        with io.open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                            _add_from_text(fh.read())
                    except Exception:
                        continue
        except Exception:
            pass

        return results

    @classmethod
    def _find_advancedskeleton_base(cls):
        """查找 AdvancedSkeleton 安装目录。"""
        checked_paths = []
        for candidate in cls._extract_adv_paths_from_shelves():
            checked_paths.append(cls._normalize_path(candidate))
            version_info = cls._is_valid_advancedskeleton_base(candidate)
            if version_info is not None:
                return cls._normalize_path(candidate), version_info

        checked_preview = "\n".join("- {0}".format(path) for path in checked_paths)
        raise RuntimeError(
            "无法从 Shelf 按钮中找到 AdvancedSkeleton 安装目录，"
            "请确认 Shelf 上有 AdvancedSkeleton 的启动按钮。"
            + ("\n已检查路径：\n{0}".format(checked_preview) if checked_preview else "")
        )

    def _get_descendant_joints(self, root_joint, prefix):
        """获取 *root_joint* 下所有以 *prefix* 开头的 joint，按自然排序返回。

        Raises:
            RuntimeError: 场景中不存在 root_joint 或找不到匹配的子 joint。
        """
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
        """从 *root_joint* 往下逐层查找，返回最近层级中第一个匹配 *prefix* 的 joint。"""
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

    def _get_active_spine_chain(self):
        """返回截断后的 spine 列表与挂在末端 spine 下的 neck 源。"""
        spine_joints = self._get_descendant_joints("pelvis", "spine")
        for idx, spine in enumerate(spine_joints):
            children = (
                cmds.listRelatives(spine, c=True, type="joint", fullPath=True) or []
            )
            neck_children = [
                c for c in children
                if self._joint_basename(c).lower().startswith("neck")
            ]
            if neck_children:
                neck_children.sort(key=self._natural_sort_key)
                return spine_joints[: idx + 1], neck_children[0]

        raise RuntimeError(
            "在 pelvis 的 spine 链各级直接子级中都没有找到 neck"
        )

    def _get_neck_source_from_spine(self):
        """返回参与 ADV 脊柱链的末端 spine 下挂的 neck 源。"""
        _, neck_source = self._get_active_spine_chain()
        return neck_source

    def _get_head_source(self):
        """获取 head 来源；若没有显式 head，则从 neck 链后续子级中自动推断。"""
        if cmds.objExists("head"):
            return "head"

        neck_source = self._get_neck_source_from_spine()
        neck_descendants = (
            cmds.listRelatives(neck_source, ad=True, type="joint", fullPath=True)
            or []
        )
        neck_chain = [neck_source]
        neck_chain.extend(
            j for j in neck_descendants
            if self._joint_basename(j).lower().startswith("neck")
        )
        neck_chain.sort(key=self._natural_sort_key)

        candidates = []
        for neck_joint in neck_chain:
            child_joints = (
                cmds.listRelatives(neck_joint, c=True, type="joint", fullPath=True)
                or []
            )
            for child in child_joints:
                if self._joint_basename(child).lower().startswith("neck"):
                    continue
                next_level_count = len(
                    cmds.listRelatives(child, c=True, type="joint", fullPath=True)
                    or []
                )
                candidates.append(
                    (next_level_count, self._natural_sort_key(child), child)
                )

        if candidates:
            candidates.sort(key=lambda item: (-item[0], item[1]))
            return candidates[0][2]

        raise RuntimeError(
            "场景中没有找到 head，且无法从 neck 链后续子级中推断 head"
        )


    def _get_twist_segment_end(self, source_prefix, side_fbx):
        """返回 twist 所在肢体段的末端骨骼。"""
        end_prefix = self.TWIST_SEGMENT_END_MAP.get(source_prefix)
        if not end_prefix:
            return None
        end_joint = "{0}{1}".format(end_prefix, side_fbx)
        if cmds.objExists(end_joint):
            return end_joint
        if source_prefix != "thigh":
            return None

        source_root = "{0}{1}".format(source_prefix, side_fbx)
        foot_joint = "foot{0}".format(side_fbx)
        if not cmds.objExists(source_root) or not cmds.objExists(foot_joint):
            return None

        source_paths = cmds.ls(source_root, long=True) or []
        foot_paths = cmds.ls(foot_joint, long=True) or []
        if not source_paths or not foot_paths:
            return None
        source_path = source_paths[0]
        current = foot_paths[0]
        while current:
            parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
            if not parents:
                break
            parent = parents[0]
            if parent == source_path:
                return current
            current = parent
        return None

    def _is_twist_on_main_bone_line(self, source_root, joint, source_prefix, side_fbx):
        """判断 twist 是否沿主骨骼方向。"""
        end_joint = self._get_twist_segment_end(source_prefix, side_fbx)
        if not end_joint:
            return True
        parent_pos = cmds.xform(source_root, q=True, ws=True, t=True)
        end_pos = cmds.xform(end_joint, q=True, ws=True, t=True)
        joint_pos = cmds.xform(joint, q=True, ws=True, t=True)
        main_vec = [b - a for a, b in zip(parent_pos, end_pos)]
        twist_vec = [b - a for a, b in zip(parent_pos, joint_pos)]
        main_len = self._distance(parent_pos, end_pos)
        twist_len = self._distance(parent_pos, joint_pos)
        if main_len <= 1e-6 or twist_len <= 1e-6:
            return False
        dot = sum(a * b for a, b in zip(main_vec, twist_vec))
        return dot / (main_len * twist_len) >= 0.95

    def _set_twist_joint_count(self, fit_joint, source_prefix):
        """根据左右两侧源骨骼子级 twist 最大数量设置 ADV twistJoints。"""
        counts = []
        for side_fbx in ("_r", "_l"):
            source_root = "{0}{1}".format(source_prefix, side_fbx)
            counts.append(len(self._get_source_twist_joints(
                source_root, source_prefix, side_fbx)))
        self._safe_set_attr(fit_joint, "twistJoints", max(counts) if counts else 0)

    def _get_source_twist_joints(self, source_root, source_prefix, side_fbx):
        """获取原 FBX 上指定肢体的有效 twist 骨骼。"""
        matched = []
        seen = set()

        def _add_if_twist(joint, strict_name=False):
            name = self._joint_basename(joint).split(":")[-1].lower()
            if "twist" not in name or "twistcor" in name:
                return
            if strict_name:
                pattern = re.compile(
                    r"^{0}.*twist.*{1}$".format(
                        re.escape(source_prefix.lower()), re.escape(side_fbx.lower())))
                if not pattern.match(name):
                    return
            key = joint.lower()
            if key not in seen:
                seen.add(key)
                matched.append(joint)

        if cmds.objExists(source_root):
            children = cmds.listRelatives(
                source_root, c=True, type="joint", fullPath=True) or []
            for joint in children:
                _add_if_twist(joint, strict_name=False)

        if not matched:
            for joint in cmds.ls(type="joint", long=True) or []:
                _add_if_twist(joint, strict_name=True)

        if not cmds.objExists(source_root):
            matched.sort(key=self._natural_sort_key)
            return matched

        parent_pos = cmds.xform(source_root, q=True, ws=True, t=True)
        distance_items = []
        for joint in matched:
            if not self._is_twist_on_main_bone_line(source_root, joint, source_prefix, side_fbx):
                continue
            joint_pos = cmds.xform(joint, q=True, ws=True, t=True)
            distance = self._distance(parent_pos, joint_pos)
            distance_items.append((distance, joint))

        distance_items.sort(key=lambda item: (item[0], self._natural_sort_key(item[1])))
        return [item[1] for item in distance_items]

    def _get_adv_twist_joints(self, adv_prefix, side_adv):
        """获取 ADV 侧指定肢体下可用于驱动源 twist 的骨骼。"""
        matched = []
        seen = set()

        part_idx = 1
        while True:
            part_name = "{0}Part{1}{2}".format(adv_prefix, part_idx, side_adv)
            if not cmds.objExists(part_name):
                break
            matched.append(part_name)
            seen.add(part_name.lower())
            part_idx += 1

        adv_root = "{0}{1}".format(adv_prefix, side_adv)
        if cmds.objExists(adv_root):
            descendants = cmds.listRelatives(
                adv_root, ad=True, type="joint", fullPath=True) or []
            side_lower = side_adv.lower()
            part_pattern = re.compile(
                r"^{0}part\d+{1}$".format(
                    re.escape(adv_prefix.lower()), re.escape(side_lower)))
            for joint in descendants:
                name = self._joint_basename(joint).split(":")[-1].lower()
                if not name.endswith(side_lower):
                    continue
                if "twist" not in name and not part_pattern.match(name):
                    continue
                key = joint.lower()
                if key in seen:
                    continue
                seen.add(key)
                matched.append(joint)

        matched.sort(key=self._natural_sort_key)
        return matched

    def _get_finger_source_chain(self, source_root, source_prefix, count=3):
        descendants = (
            cmds.listRelatives(source_root, ad=True, type="joint", fullPath=True) or []
        )
        matched = []
        for j in descendants:
            name = self._joint_basename(j).split(":")[-1].lower()
            if "metacarpal" in name or "twist" in name:
                continue
            if re.match(r"^{0}[_-]?\d+".format(source_prefix.lower()), name):
                matched.append(j)
        matched.sort(key=self._natural_sort_key)
        return matched[:count]

    def _remove_fit_finger_segments(self, fit_prefix, start_index):
        for i in range(start_index, 5):
            node = "{0}Finger{1}".format(fit_prefix, i)
            if cmds.objExists(node):
                cmds.delete(node)

    def _match_finger_chain(self, fit_chain, source_root, source_prefix):
        source_joints = self._get_finger_source_chain(source_root, source_prefix, 4)
        keep_count = min(len(source_joints), len(fit_chain))
        if keep_count <= 0:
            raise RuntimeError("{0} finger chain not found".format(source_prefix))

        fit_prefix = re.match(r"^([A-Za-z]+)Finger", fit_chain[0]).group(1)
        for fit_joint, src_joint in zip(fit_chain[:keep_count], source_joints[:keep_count]):
            cmds.matchTransform(fit_joint, src_joint, pos=True, rot=True)
        self._remove_fit_finger_segments(fit_prefix, keep_count + 1)
    def _duplicate_joint_to_fit(self, source_joint, new_name, parent_fit_node,
                                force_center=False, no_control=True):
        """复制源 joint 到 FitSkeleton。"""
        pos = cmds.xform(source_joint, q=True, ws=True, t=True)
        rot = cmds.xform(source_joint, q=True, ws=True, ro=True)

        if force_center:
            pos = self._zero_center_axis(pos)

        cmds.select(clear=True)
        new_joint = cmds.joint(name=new_name)
        cmds.xform(new_joint, ws=True, t=pos)
        cmds.xform(new_joint, ws=True, ro=rot)
        cmds.parent(new_joint, parent_fit_node)
        # inbetween 标记（仅 no_control=True 时添加）
        if no_control:
            cmds.addAttr(new_joint, ln="tempInbetweener", at="bool", dv=1, k=True)
            cmds.addAttr(new_joint, ln="noControl", at="bool", dv=1, k=True)
            cmds.setAttr("{0}.noControl".format(new_joint), 1)

        for attr in ("fat", "fatFront", "fatWidth"):
            parent_val = 0.0
            if cmds.attributeQuery(attr, node=parent_fit_node, exists=True):
                parent_val = cmds.getAttr("{0}.{1}".format(parent_fit_node, attr))
            cmds.addAttr(new_joint, ln=attr, at="double", dv=parent_val, k=False)

        return new_joint
    def _setup_spine(self):
        """按截断后的 spine 链创建 ADV 脊柱分段。"""
        pelvis = "pelvis"
        if not cmds.objExists(pelvis):
            cmds.warning("场景中没有找到对象: {0}".format(pelvis))
            return

        try:
            spine_joints, _neck = self._get_active_spine_chain()
        except RuntimeError as exc:
            cmds.warning("{0}".format(exc))
            return
        if not spine_joints:
            cmds.warning("pelvis 层级下没有找到 spine* 关节")
            return

        # Spine1 对齐到第一个 spine，Chest 对齐到最后一个 spine
        spine1_source = spine_joints[0]
        chest_source = spine_joints[-1]

        cmds.matchTransform("Spine1", spine1_source, pos=True)
        cmds.matchTransform("Chest", chest_source, pos=True)

        # 确保 inbetweenJoints 清零
        self._safe_set_attr("Root",   "inbetweenJoints", 0)
        self._safe_set_attr("Spine1", "inbetweenJoints", 0)

        # 记录生成的中间骨骼名称，供约束映射使用
        self._spine_mid_names = []  # Spine1 → Chest 之间
        # Spine1 → 中间骨骼 → Chest 链
        mid_sources = spine_joints[1:-1]  # 除第一个和最后一个之外的所有 spine
        current_parent = "Spine1"
        for i, src in enumerate(mid_sources):
            mid_name = "Spine{0}".format(i + 2)  # Spine2, Spine3, Spine4, ...
            self._duplicate_joint_to_fit(src, mid_name, current_parent,
                                         force_center=True, no_control=False)
            self._spine_mid_names.append(mid_name)
            current_parent = mid_name

        if mid_sources:
            self._safe_parent("Chest", current_parent)
    def _setup_neck(self):
        """将 neck 到 head 之间直系链路上的中间骨骼复制到 ADV FitSkeleton 层级，
        并形成一条完整的层级链。

        脖子处不添加 inbetween 属性标记，保留原始的独立 FK 控制器。

        示例（neck_01 → neck_02 → neck_03 → head）：
            Neck → Neck1(neck_02) → Neck2(neck_03) → Head
        """
        try:
            neck_source = self._get_neck_source_from_spine()
        except RuntimeError as exc:
            cmds.warning("{0}，跳过颈部骨骼复制".format(exc))
            return

        try:
            head_source = self._get_head_source()
        except RuntimeError as exc:
            cmds.warning("{0}，跳过颈部骨骼复制".format(exc))
            return

        # 确保 inbetweenJoints 清零
        self._safe_set_attr("Neck", "inbetweenJoints", 0)

        # 从 head 的 fullPath 回溯到 neck_source，提取直系链路上的中间关节
        head_long = cmds.ls(head_source, long=True)[0]
        neck_long = cmds.ls(neck_source, long=True)[0]

        if neck_long not in head_long:
            cmds.warning("head 不在 neck 链的后代中，跳过颈部骨骼复制")
            return

        path_parts = head_long.split("|")
        neck_short = neck_long.split("|")[-1]
        head_short = head_long.split("|")[-1]

        try:
            neck_idx = path_parts.index(neck_short)
            head_idx = path_parts.index(head_short)
        except ValueError:
            cmds.warning("无法解析 neck 到 head 的路径，跳过颈部骨骼复制")
            return

        # 中间关节（不含 neck_source 自身，不含 head）
        between_names = path_parts[neck_idx + 1 : head_idx]

        # 形成链式层级：Neck → Neck1 → Neck2 → ... → Head
        current_parent = "Neck"
        for i, joint_name in enumerate(between_names, start=1):
            joint_full = "|".join(path_parts[: neck_idx + 1 + i])
            part_name = "Neck{0}".format(i)
            src = joint_full if cmds.objExists(joint_full) else joint_name
            if not cmds.objExists(src):
                cmds.warning("找不到颈部中间骨骼 {0}，跳过".format(joint_name))
                continue

            pos = cmds.xform(src, q=True, ws=True, t=True)
            rot = cmds.xform(src, q=True, ws=True, ro=True)
            pos = self._zero_center_axis(pos)  # 中心线骨骼侧向归零

            cmds.select(clear=True)
            new_joint = cmds.joint(name=part_name)
            cmds.xform(new_joint, ws=True, t=pos)
            cmds.xform(new_joint, ws=True, ro=rot)
            cmds.parent(new_joint, current_parent)

            current_parent = part_name

        # 如果有 Neck1/2/...，Head 要挂到最后一个下面
        if between_names:
            self._safe_parent("Head", current_parent)
    def _ensure_fit_skeleton_ready(self):
        """确保 FitSkeleton 节点存在并补齐必要属性。"""
        if not cmds.objExists("FitSkeleton"):
            raise RuntimeError("FitSkeleton 不存在，无法继续 Build")

        self._mel_cmd("EnsureFitSkeletonAttributes")
        self._mel_cmd_if_exists("EnsureAllFitJointAttrs")

        for attr_name in ("preRebuildScript", "postRebuildScript"):
            if not cmds.attributeQuery(attr_name, node="FitSkeleton", exists=True):
                cmds.addAttr("FitSkeleton", ln=attr_name, dt="string")

    @staticmethod
    def _delete_useless_bones():
        """删除不需要的 Eye / Jaw 骨骼。"""
        for bone in ("Eye", "Jaw"):
            if cmds.objExists(bone):
                cmds.delete(bone)
    # FitSkeleton 手指名称前缀 → 场景 FBX 骨骼搜索前缀的映射
    _FINGER_DETECT_MAP = [
        ("Thumb",  "thumb"),
        ("Index",  "index"),
        ("Middle", "middle"),
        ("Ring",   "ring"),
        ("Pinky",  "pinky"),
    ]

    def _detect_scene_finger_counts(self):
        counts = {}
        hand = self.HAND_SOURCE
        if not cmds.objExists(hand):
            return counts
        for _fit_prefix, fbx_prefix in self._FINGER_DETECT_MAP:
            counts[fbx_prefix] = len(self._get_finger_source_chain(hand, fbx_prefix, 4))
        return counts

    def _remove_fit_fingers_and_cup(self, finger_counts):
        # build 前：根据场景骨骼数量直接在 FitSkeleton 上删除多余手指段和 Cup，
        # 让 ReBuildAdvancedSkeleton 不会生成对应控制器。
        for fit_prefix, fbx_prefix in self._FINGER_DETECT_MAP:
            keep_count = finger_counts.get(fbx_prefix, 0)
            start_index = 1 if keep_count <= 0 else keep_count + 1
            self._remove_fit_finger_segments(fit_prefix, start_index)

        # ring 和 pinky 都缺失时，FitSkeleton 上的 Cup 一并删除
        if finger_counts.get("ring", 0) <= 0 and finger_counts.get("pinky", 0) <= 0:
            if cmds.objExists("Cup"):
                try:
                    cmds.delete("Cup")
                except Exception:
                    pass

    def _remove_extra_adv_fingers(self, finger_counts):
        for fit_prefix, fbx_prefix in self._FINGER_DETECT_MAP:
            keep_count = finger_counts.get(fbx_prefix, 0)
            patterns = []
            if keep_count <= 0:
                patterns.append("*{0}Finger*_*".format(fit_prefix))
            else:
                for i in range(keep_count + 1, 5):
                    patterns.append("*{0}Finger{1}_*".format(fit_prefix, i))
                    patterns.append("FK{0}Finger{1}_*".format(fit_prefix, i))
                    patterns.append("IK{0}Finger{1}_*".format(fit_prefix, i))
            nodes = set()
            for pattern in patterns:
                nodes.update(cmds.ls(pattern, type="transform") or [])
            for node in sorted(nodes, key=lambda x: x.count("|"), reverse=True):
                if cmds.objExists(node):
                    try:
                        cmds.delete(node)
                    except Exception:
                        pass

        # ring 和 pinky 都缺失时，Cup 控制器也一并删除
        if finger_counts.get("ring", 0) <= 0 and finger_counts.get("pinky", 0) <= 0:
            cup_nodes = set()
            for pattern in ("Cup_*", "FKCup_*", "IKCup_*"):
                cup_nodes.update(cmds.ls(pattern, type="transform") or [])
            for node in sorted(cup_nodes, key=lambda x: x.count("|"), reverse=True):
                if cmds.objExists(node):
                    try:
                        cmds.delete(node)
                    except Exception:
                        pass
    @staticmethod
    def _remove_root_bone():
        """删除源骨架 root，并将子级提到世界层级。"""
        all_joints = cmds.ls(type="joint", long=True) or []
        root_joints = [
            j for j in all_joints
            if j.split("|")[-1].lower() == "root"
        ]
        if not root_joints:
            return False

        for root_jnt in root_joints:
            if not cmds.objExists(root_jnt):
                continue
            # 将 root 的所有子级解除到世界空间
            children = cmds.listRelatives(root_jnt, children=True, fullPath=True) or []
            if children:
                cmds.parent(children, world=True)
            cmds.delete(root_jnt)

        return True

    _ADV_STUB_WINDOW = "_adv_ui_stubs_win"

    # ADV MEL 内部会查询的 UI 控件：(控件类型, 名称, 创建参数)
    _ADV_UI_STUB_DEFS = [
        ("checkBox",   "asBodyZUpAxisCheckBox",            {}),
        ("checkBox",   "asAdvancedSkeletonZUpAxisCheckBox", {}),
        ("checkBox",   "asBodyGameEngineCheckBox",         {"value": False}),
        ("checkBox",   "asBodyOffsetParentMatrixCheckBox", {"value": False}),
        ("checkBox",   "asBodySubControllersCheckBox",     {"value": False}),
        ("checkBox",   "asBodyExtraControllersCheckBox",   {"value": False}),
        ("checkBox",   "asBodyMirTransCheckBox",           {"value": False}),
        ("checkBox",   "asVisGeo",                         {"value": False}),
        ("checkBox",   "asRebuildConnections",             {"value": True}),
        ("checkBox",   "asLockCenterJoints",               {"value": False}),
        ("checkBox",   "asVisPoleVector",                  {"value": False}),
        ("checkBox",   "asVisJointOrient",                 {"value": False}),
        ("checkBox",   "asVisJointAxis",                   {"value": False}),
        ("button",     "asToggleFitSkeletonButton",        {}),
        ("button",     "asBuildAdvancedSkeletonButton",    {}),
        ("button",     "asToggleFitFaceButton",            {}),
        ("button",     "asBuildAdvancedFaceButton",        {}),
        ("button",     "asGoToBuildPoseFaceButton",        {}),
        ("text",       "asBodyText",                       {}),
        ("text",       "asFaceText",                       {}),
        ("rowLayout",  "asFaceRebuildKeepBSRowLayout",     {}),
        ("optionMenu", "asVisGeoType",                     {"items": ["cylinders", "boxes", "spheres"]}),
        ("floatSliderGrp", "asVisGap",                     {"value": 1.0}),
        ("floatField", "ScaleCCFloatField",                {"value": 1.0}),
    ]


    @classmethod
    def _ensure_adv_ui_stubs(cls):
        """在隐藏窗口里预创建 ADV MEL 内部会查询的 UI 控件。"""
        if cmds.window(cls._ADV_STUB_WINDOW, exists=True):
            cmds.deleteUI(cls._ADV_STUB_WINDOW, window=True)

        cmds.window(cls._ADV_STUB_WINDOW, title="ADV Stubs", visible=False)
        cmds.columnLayout()

        is_z_up = cmds.upAxis(q=True, ax=True) == "z"

        for ctrl_type, ctrl_name, params in cls._ADV_UI_STUB_DEFS:
            if cmds.control(ctrl_name, exists=True):
                continue

            if ctrl_type == "checkBox":
                # Z-up 相关 checkbox 默认跟随场景，其余优先使用配置值
                default_val = params.get(
                    "value",
                    is_z_up if "ZUp" in ctrl_name else False,
                )
                cmds.checkBox(ctrl_name, value=default_val)
            elif ctrl_type == "floatField":
                cmds.floatField(ctrl_name, **params)
            elif ctrl_type == "optionMenu":
                cmds.optionMenu(ctrl_name)
                for item_label in params.get("items", []):
                    cmds.menuItem(label=item_label, parent=ctrl_name)
            elif ctrl_type == "floatSliderGrp":
                cmds.floatSliderGrp(ctrl_name, value=params.get("value", 0.0))
            elif ctrl_type == "button":
                cmds.button(ctrl_name, label=ctrl_name)
            elif ctrl_type == "text":
                cmds.text(ctrl_name, label=ctrl_name)
            elif ctrl_type == "rowLayout":
                # rowLayout 是容器，建后立即 setParent 退出，避免后续控件被塞入
                cmds.rowLayout(ctrl_name, numberOfColumns=1)
                cmds.setParent("..")

        cmds.setParent("..")

    @staticmethod
    def _safe_match_transform(fit_node, source_node, pos=True, rot=False):
        """源或目标不存在时跳过对齐。"""
        if not fit_node or not source_node:
            return False
        if not cmds.objExists(fit_node) or not cmds.objExists(source_node):
            return False
        try:
            cmds.matchTransform(fit_node, source_node, pos=pos, rot=rot)
            return True
        except Exception as exc:
            cmds.warning("跳过对齐 {0} <- {1}: {2}".format(fit_node, source_node, exc))
            return False

    def _align_fit_skeleton(self):
        """将 FitSkeleton 控制器对齐到源骨骼；缺失则跳过。"""
        # 1. 全局缩放（结合身高 + 肩宽修正）
        try:
            head_source = self._get_head_source()
            head_height = self._get_height(cmds.xform(head_source, q=True, ws=True, t=True))
        except RuntimeError as exc:
            cmds.warning("{0}，使用默认 ADV 缩放".format(exc))
            head_source = None
            head_height = 10.0

        try:
            shoulder_dist = self._distance(
                cmds.xform("upperarm_l", q=True, ws=True, rp=True),
                cmds.xform("upperarm_r", q=True, ws=True, rp=True),
            )
        except Exception:
            shoulder_dist = head_height * self.SHOULDER_HEIGHT_RATIO_REF
        ratio = shoulder_dist / head_height if head_height else self.SHOULDER_HEIGHT_RATIO_REF
        correction = ratio / self.SHOULDER_HEIGHT_RATIO_REF
        self._correction = correction  # 原始修正因子，供脖子等控制器缩放使用
        # 躯干控制器缩放修正：仅当 correction 低于阈值时才缩小控制器，
        # 避免正常/大体型模型的控制器被额外缩放
        ctrl_correction_threshold = 0.78
        if correction >= ctrl_correction_threshold:
            self._body_correction = 1.0  # 正常范围内，控制器不做额外缩放
        else:
            self._body_correction = correction / ctrl_correction_threshold  # 超出阈值的部分才缩放

        base_scale = head_height / 10.0
        final_scale = base_scale * correction
        self._set_uniform_scale("FitSkeleton", final_scale)
        # 2. 第一阶段：下半身 + 脊柱基础
        for fit_node, source_node in self.BODY_POSITION_MAP_PHASE1:
            self._safe_match_transform(fit_node, source_node, pos=True)
        # 3. twist joint 数量
        for fit_joint, src_joint in self.TWIST_JOINT_MAP:
            self._set_twist_joint_count(fit_joint, src_joint)
        # 4. 脚趾
        foot_children = (
            cmds.listRelatives("foot_r", c=True, type="joint", fullPath=True) or []
        ) if cmds.objExists("foot_r") else []
        if foot_children:
            self._safe_match_transform("Toes", foot_children[0], pos=True)
        else:
            cmds.warning("foot_r 下没有找到 joint 子级，跳过 Toes 对齐")
        # 5. 脊柱分段
        self._setup_spine()
        # 6. Neck / Head 特殊处理
        try:
            neck_source = self._get_neck_source_from_spine()
        except RuntimeError as exc:
            cmds.warning("{0}，跳过 Neck 对齐".format(exc))
            neck_source = None
        self._safe_match_transform("Neck", neck_source, pos=True)
        self._safe_match_transform("Head", head_source, pos=True)
        # 7. 第二阶段：其余上半身
        for fit_node, source_node in self.BODY_POSITION_MAP_PHASE2:
            self._safe_match_transform(fit_node, source_node, pos=True)
        # 8. 颈部分段
        self._setup_neck()
        # 9. Cup（手掌中心）位置
        # 按优先级取最外侧存在的手指来计算 Cup 位置
        if cmds.objExists(self.HAND_SOURCE) and cmds.objExists("Cup"):
            hand_pos = cmds.xform(self.HAND_SOURCE, q=True, ws=True, t=True)
            cup_ref_pos = hand_pos  # fallback
            for outer_prefix in ("pinky", "ring", "middle", "index", "thumb"):
                try:
                    outer_joints = self._get_descendant_joints(self.HAND_SOURCE, outer_prefix)
                    cup_ref_pos = cmds.xform(outer_joints[0], q=True, ws=True, t=True)
                    break
                except RuntimeError:
                    continue
            cmds.xform("Cup", ws=True, t=self._midpoint(hand_pos, cup_ref_pos))
        # 10. 手指对齐（只对齐场景中存在的手指）
        for fit_chain, prefix in self.FINGER_MAP:
            try:
                self._match_finger_chain(fit_chain, self.HAND_SOURCE, prefix)
            except RuntimeError:
                pass  # 该手指在场景中不存在，已从 FitSkeleton 中删除

    def _scale_control_curve(self, ctrl_name, scale_value):
        """按 pivot 缩放控制器曲线 CV。"""
        if not cmds.objExists(ctrl_name):
            cmds.warning("控制器 {0} 不存在，跳过缩放。".format(ctrl_name))
            return

        # 获取控制器下所有 nurbsCurve shape
        shapes = cmds.listRelatives(ctrl_name, shapes=True, type="nurbsCurve",
                                    fullPath=True) or []
        if not shapes:
            cmds.warning("控制器 {0} 下没有 nurbsCurve shape，跳过缩放。".format(ctrl_name))
            return

        # 收集所有 CV
        cv_list = []
        for shape in shapes:
            num_cvs = cmds.getAttr("{0}.controlPoints".format(shape), size=True)
            if num_cvs > 0:
                cv_list.append("{0}.cv[0:{1}]".format(shape, num_cvs - 1))

        if not cv_list:
            return

        # 以控制器的 rotatePivot 为中心缩放 CV
        pivot = cmds.xform(ctrl_name, q=True, ws=True, rp=True)
        cmds.select(cv_list, replace=True)
        cmds.scale(scale_value, scale_value, scale_value,
                   pivot=(pivot[0], pivot[1], pivot[2]),
                   relative=True)
        cmds.select(clear=True)

    def _scale_finger_controls(self, scale_value=0.7):
        """缩放所有手指 FK 控制器曲线。"""
        finger_prefixes = ("Thumb", "Index", "Middle", "Ring", "Pinky")
        sides = ("_L", "_R")

        scaled_count = 0
        for prefix in finger_prefixes:
            for side in sides:
                pattern = "FK{0}Finger*{1}".format(prefix, side)
                matches = cmds.ls(pattern, type="transform") or []
                for ctrl in matches:
                    shapes = cmds.listRelatives(ctrl, shapes=True,
                                                type="nurbsCurve") or []
                    if shapes:
                        self._scale_control_curve(ctrl, scale_value)
                        scaled_count += 1
    # ADV 骨骼名 → FBX 原始骨骼名 的映射表
    # ADV build 后中心线骨骼以 _M 结尾，左右侧以 _L/_R 结尾
    # 映射格式：(ADV骨骼名, FBX骨骼名)
    # _L/_R 侧的映射会自动生成双侧
    ADV_TO_FBX_MAP_CENTER = [
        ("Root_M",   "pelvis"),
    ]

    ADV_TO_FBX_MAP_SIDED = [
        # (ADV名称后缀, FBX名称前缀_r, FBX名称前缀_l)
        # 如果 _l 为 None，则自动从 _r 推导（把 _r 换成 _l）
        ("Hip",      "thigh_r",      "thigh_l"),
        ("Knee",     "calf_r",       "calf_l"),
        ("Ankle",    "foot_r",       "foot_l"),
        ("Toes",     "ball_r",       "ball_l"),
        ("Scapula",  "clavicle_r",   "clavicle_l"),
        ("Shoulder", "upperarm_r",   "upperarm_l"),
        ("Elbow",    "lowerarm_r",   "lowerarm_l"),
        ("Wrist",    "hand_r",       "hand_l"),
    ]

    # 手指映射（ADV手指名 → FBX手指前缀）
    ADV_TO_FBX_FINGER_MAP = [
        ("ThumbFinger1",  "thumb_01"),
        ("ThumbFinger2",  "thumb_02"),
        ("ThumbFinger3",  "thumb_03"),
        ("ThumbFinger4",  "thumb_04"),
        ("IndexFinger1",  "index_01"),
        ("IndexFinger2",  "index_02"),
        ("IndexFinger3",  "index_03"),
        ("IndexFinger4",  "index_04"),
        ("MiddleFinger1", "middle_01"),
        ("MiddleFinger2", "middle_02"),
        ("MiddleFinger3", "middle_03"),
        ("MiddleFinger4", "middle_04"),
        ("RingFinger1",   "ring_01"),
        ("RingFinger2",   "ring_02"),
        ("RingFinger3",   "ring_03"),
        ("RingFinger4",   "ring_04"),
        ("PinkyFinger1",  "pinky_01"),
        ("PinkyFinger2",  "pinky_02"),
        ("PinkyFinger3",  "pinky_03"),
        ("PinkyFinger4",  "pinky_04"),
    ]

    def _constrain_adv_to_fbx(self):
        """用 ADV 骨骼约束驱动原 FBX 骨骼。"""
        _constrained_count = [0]

        def _exists(name):
            return cmds.objExists(name)

        def _do_pos_orient_scale(adv_joint, fbx_joint):
            """pointConstraint + orientConstraint + scaleConstraint（标准三约束）。"""
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.pointConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                cmds.orientConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                cmds.scaleConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                _constrained_count[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False

        def _do_pos_orient(adv_joint, fbx_joint):
            """pointConstraint + orientConstraint（用于 twist 骨骼等）。"""
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.pointConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                cmds.orientConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                _constrained_count[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False

        def _do_parent(adv_joint, fbx_joint):
            """parentConstraint（用于 correctiveRoot 等）。"""
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.parentConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                _constrained_count[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False

        def _do_orient_only(adv_joint, fbx_joint):
            """orientConstraint only（用于 real 骨骼等）。"""
            if not _exists(adv_joint) or not _exists(fbx_joint):
                return False
            try:
                cmds.orientConstraint(adv_joint, fbx_joint, mo=True, weight=1.0)
                _constrained_count[0] += 1
                return True
            except Exception as exc:
                cmds.warning("约束 {0} -> {1} 失败: {2}".format(adv_joint, fbx_joint, exc))
                return False
        # 1. 中心线骨骼（pelvis / spine / neck / head）
        for adv_name, fbx_name in self.ADV_TO_FBX_MAP_CENTER:
            _do_pos_orient_scale(adv_name, fbx_name)
        # 2. Spine 骨骼（Spine1 + 中间骨骼 + Chest）
        spine_joints = sorted(
            [j for j in (cmds.ls("spine_*", type="joint") or [])
             if re.match(r"^spine_\d+$", j)],
            key=self._natural_sort_key
        )
        if spine_joints:
            # Spine1 对齐第一个，Chest 对齐最后一个
            _do_pos_orient_scale("Spine1_M", spine_joints[0])

            # 中间骨骼（Spine1A, Spine1B, ...）
            mid_joints = spine_joints[1:-1]
            for i, fbx_jnt in enumerate(mid_joints):
                adv_name = "{0}_M".format(self._spine_mid_names[i]) if i < len(getattr(self, '_spine_mid_names', [])) else None
                if adv_name:
                    _do_pos_orient_scale(adv_name, fbx_jnt)

            _do_pos_orient_scale("Chest_M", spine_joints[-1])
        # 3. Neck inbetween 骨骼
        try:
            neck_source = self._get_neck_source_from_spine()
            head_source = self._get_head_source()

            head_long = cmds.ls(head_source, long=True)[0]
            neck_long = cmds.ls(neck_source, long=True)[0]

            if neck_long in head_long:
                path_parts = head_long.split("|")
                neck_short = neck_long.split("|")[-1]
                head_short = head_long.split("|")[-1]
                neck_idx = path_parts.index(neck_short)
                head_idx = path_parts.index(head_short)
                between_names = path_parts[neck_idx + 1: head_idx]

                _do_pos_orient_scale("Neck_M", neck_source)
                for i, joint_name in enumerate(between_names, start=1):
                    _do_pos_orient_scale("Neck{0}_M".format(i), joint_name)
                _do_pos_orient_scale("Head_M", head_source)
            else:
                _do_pos_orient_scale("Neck_M", neck_source)
                _do_pos_orient_scale("Head_M", head_source)
        except Exception as exc:
            cmds.warning("跳过 Neck/Head 原 FBX 约束对齐: {0}".format(exc))
        # 4. 左右侧骨骼
        for adv_suffix, fbx_r, fbx_l in self.ADV_TO_FBX_MAP_SIDED:
            _do_pos_orient_scale("{0}_R".format(adv_suffix), fbx_r)
            _do_pos_orient_scale("{0}_L".format(adv_suffix), fbx_l)
        # 5. Twist 骨骼（识别 ADV 肢体子级 twist/Part 驱动原 FBX twist）
        twist_map = [
            ("Hip",      "thigh"),
            ("Knee",     "calf"),
            ("Shoulder", "upperarm"),
            ("Elbow",    "lowerarm"),
        ]
        for adv_prefix, fbx_prefix in twist_map:
            for side_adv, side_fbx in [("_R", "_r"), ("_L", "_l")]:
                source_root = "{0}{1}".format(fbx_prefix, side_fbx)
                adv_twists = self._get_adv_twist_joints(adv_prefix, side_adv)
                fbx_twists = self._get_source_twist_joints(
                    source_root, fbx_prefix, side_fbx)
                for adv_twist, fbx_twist in zip(adv_twists, fbx_twists):
                    _do_pos_orient(adv_twist, fbx_twist)
        # 6. correctiveRoot 骨骼（parentConstraint）
        corrective_map = [
            ("Hip",      "thigh"),
            ("Knee",     "calf"),
            ("Shoulder", "upperarm"),
            ("Elbow",    "lowerarm"),
        ]
        for adv_prefix, fbx_prefix in corrective_map:
            for side_adv, side_fbx in [("_R", "_r"), ("_L", "_l")]:
                fbx_corrective = "{0}_correctiveRoot{1}".format(fbx_prefix, side_fbx)
                if _exists(fbx_corrective):
                    # correctiveRoot 用其同名 ADV 骨骼做 parentConstraint
                    adv_joint = "{0}{1}".format(adv_prefix, side_adv)
                    _do_parent(adv_joint, fbx_corrective)
        # 7. real 骨骼（orientConstraint only）
        real_map = [
            ("Hip",      "thigh"),
            ("Knee",     "calf"),
            ("Shoulder", "upperarm"),
            ("Elbow",    "lowerarm"),
        ]
        for adv_prefix, fbx_prefix in real_map:
            for side_adv, side_fbx in [("_R", "_r"), ("_L", "_l")]:
                fbx_real = "{0}_real{1}".format(fbx_prefix, side_fbx)
                if _exists(fbx_real):
                    adv_joint = "{0}{1}".format(adv_prefix, side_adv)
                    _do_orient_only(adv_joint, fbx_real)
        # 8. 手指骨骼（含 metacarpal 掌骨）
        for adv_finger, fbx_prefix in self.ADV_TO_FBX_FINGER_MAP:
            for side_adv, side_fbx in [("_R", "_r"), ("_L", "_l")]:
                adv_name = "{0}{1}".format(adv_finger, side_adv)
                fbx_name = "{0}{1}".format(fbx_prefix, side_fbx)
                _do_pos_orient_scale(adv_name, fbx_name)

        # metacarpal（掌骨）约束
        finger_metacarpal_map = [
            ("IndexFinger1",  "index_metacarpal"),
            ("MiddleFinger1", "middle_metacarpal"),
            ("RingFinger1",   "ring_metacarpal"),
            ("PinkyFinger1",  "pinky_metacarpal"),
        ]
        for adv_finger, fbx_prefix in finger_metacarpal_map:
            for side_adv, side_fbx in [("_R", "_r"), ("_L", "_l")]:
                fbx_meta = "{0}{1}".format(fbx_prefix, side_fbx)
                if _exists(fbx_meta):
                    adv_name = "{0}{1}".format(adv_finger, side_adv)
                    _do_pos_orient_scale(adv_name, fbx_meta)
        # 9. Toes（脚趾）
        for side_adv, side_fbx in [("_R", "_r"), ("_L", "_l")]:
            # 尝试 ball_r/ball_l
            fbx_ball = "ball{0}".format(side_fbx)
            if _exists(fbx_ball):
                _do_pos_orient_scale("Toes{0}".format(side_adv), fbx_ball)
            else:
                # 回退到 foot 下第一个子骨骼
                foot_fbx = "foot{0}".format(side_fbx)
                if _exists(foot_fbx):
                    foot_children = cmds.listRelatives(foot_fbx, c=True, type="joint") or []
                    if foot_children:
                        _do_pos_orient_scale("Toes{0}".format(side_adv), foot_children[0])


    @staticmethod
    def _add_root_vv():
        """在原 FBX 的 pelvis 骨骼上方创建一个 root 根骨骼，作为 pelvis 的父级。"""
        if not cmds.objExists("pelvis"):
            cmds.warning("pelvis 不存在，跳过创建 root")
            return

        # 获取 pelvis 当前的父节点
        pelvis_parents = cmds.listRelatives("pelvis", parent=True, fullPath=True) or []

        # 创建 root 根骨骼在世界原点
        cmds.select(clear=True)
        root_jnt = cmds.joint(name="root", position=[0, 0, 0])
        # 设置 joint 半径与 pelvis 一致
        radius = cmds.getAttr("pelvis.radius")
        cmds.setAttr("{0}.radius".format(root_jnt), radius)

        # 如果 pelvis 有父节点，先把 root 放到同一父级下
        if pelvis_parents:
            cmds.parent(root_jnt, pelvis_parents[0])

        # 将 pelvis 挂到 root 下
        cmds.parent("pelvis", root_jnt)

    def build(self, generate_root=True):
        """构建 AdvancedSkeleton 控制器。"""
        cmds.currentUnit(linear="cm")

        # source ADV MEL
        mel_path = self._normalize_path(
            os.path.join(self.advancedskeleton_base, self._adv_mel_name)
        )
        mel.eval('source "{0}";'.format(mel_path))

        # 创建 ADV 内部依赖的 UI 控件存根（避免 MEL 过程访问不存在的控件报错）
        self._ensure_adv_ui_stubs()

        self._remove_root_bone()

        # 用 ADV 接口定位并导入 biped FitSkeleton
        if not cmds.objExists("FitSkeleton"):
            adv_base = mel.eval("asGetScriptLocation;")
            biped_ma = "{0}/{1}/fitSkeletons/biped.ma".format(adv_base, self._adv_files_dirname)
            mel.eval('file -import -rpr "AdvancedSkeleton" -options "v=0" "{0}";'.format(biped_ma))

        # 补齐属性（EnsureAllFitJointAttrs 仅 ADV 5.813+ 才有）
        self._mel_cmd("EnsureFitSkeletonAttributes")
        self._mel_cmd_if_exists("EnsureAllFitJointAttrs")
        for attr_name in ("preRebuildScript", "postRebuildScript"):
            if not cmds.attributeQuery(attr_name, node="FitSkeleton", exists=True):
                cmds.addAttr("FitSkeleton", ln=attr_name, dt="string")

        self._finger_source_counts = self._detect_scene_finger_counts()

        self._align_fit_skeleton()
        self._delete_useless_bones()
        self._remove_fit_fingers_and_cup(self._finger_source_counts)

        self._mel_cmd("FitModeManualUpdate")
        self._mel_cmd("ReBuildAdvancedSkeleton")
        self._remove_extra_adv_fingers(self._finger_source_counts)
        # 缩放 HipSwinger_M 控制器
        self._scale_control_curve("HipSwinger_M", 0.5)
        # 根据体型修正因子成组缩放躯干控制器
        torso_control_groups = (
            ("FKSpine1_M", "IKSpine2_M", "IKhybridSpine2_M"),
            ("FKChest_M", "IKSpine3_M", "IKhybridSpine3_M"),
        )
        for control_group in torso_control_groups:
            for ctrl_name in control_group:
                self._scale_control_curve(ctrl_name, self._body_correction)
        # 缩放 spine 中间骨骼 FK 控制器（FKSpine2_M, FKSpine3_M, ...）
        for name in getattr(self, '_spine_mid_names', []):
            ctrl = "FK{0}_M".format(name)
            if cmds.objExists(ctrl):
                shapes = cmds.listRelatives(ctrl, shapes=True, type="nurbsCurve") or []
                if shapes:
                    self._scale_control_curve(ctrl, self._body_correction)
        # 根据体型修正因子放大脖子控制器
        # 1/correction 取倒数确保全部放大，再乘 1.5 基础放大系数
        neck_scale = (1.0 / self._correction) * 1.5
        self._scale_control_curve("FKNeck_M", neck_scale)
        # 缩放所有手指控制器
        self._scale_finger_controls(0.7)
        # 在 Root_M 上方添加 root 骨骼
        if generate_root:
            self._add_root_vv()
        # 将 ADV 骨骼约束到原 FBX 骨骼
        self._constrain_adv_to_fbx()
        # 隐藏 ADV 的 DeformationSystem 层级
        if cmds.objExists("DeformationSystem"):
            cmds.setAttr("DeformationSystem.visibility", 0)

        cmds.select(clear=True)

    # ADV build 产生的顶层节点，fallback 删除时清理用
    _ADV_BUILD_TOP_NODES = (
        "Group", "DeformationSystem", "MotionSystem", "Aims",
        "Geometry", "FitSkeletonVisualizers",
        "Sets", "DeformSet", "ControlSet", "AllSet",
    )

    def delete_controller(self):
        """删除 ADV 控制器；老版本无 asDeleteAdvanced 时手动 fallback。"""
        mel_path = self._normalize_path(
            os.path.join(self.advancedskeleton_base, self._adv_mel_name)
        )
        mel.eval('source "{0}";'.format(mel_path))
        self._ensure_adv_ui_stubs()

        # 优先用 ADV 自带 asDeleteAdvanced，缺失则手动 fallback
        if not self._mel_cmd_if_exists("DeleteAdvanced"):
            self._fallback_delete_advanced()

        if cmds.objExists("FitSkeleton"):
            cmds.delete("FitSkeleton")
        cmds.select(clear=True)

    @classmethod
    def _fallback_delete_advanced(cls):
        """老版本 ADV 无 asDeleteAdvanced 时手动清理 build 产物。"""
        # Geometry 下的 mesh 释放到世界，避免被一起删
        if cmds.objExists("Geometry"):
            geo_children = cmds.listRelatives("Geometry", type="transform", c=True) or []
            if geo_children:
                try:
                    cmds.parent(geo_children, world=True)
                except Exception:
                    pass

        # 先删依赖类节点，避免删父级时触发 evaluate 报错
        leaf_nodes = cmds.ls("IKCurveInfo*", "*MultiplyDivide*", type=("curveInfo",)) or []
        for node in leaf_nodes:
            try:
                cmds.delete(node)
            except Exception:
                pass

        for node in cls._ADV_BUILD_TOP_NODES:
            if cmds.objExists(node):
                try:
                    cmds.delete(node)
                except Exception as exc:
                    cmds.warning("Failed to delete '{0}': {1}".format(node, exc))


if __name__ == "__main__":
    FbxToADV().build()
