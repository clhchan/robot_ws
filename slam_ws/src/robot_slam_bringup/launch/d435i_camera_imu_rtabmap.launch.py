"""仅使用 D435i 红外双目和内置 IMU 启动 OpenVINS 里程计与 RTAB-Map 建图/重定位."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from launch_ros.parameter_descriptions import ParameterValue
from nav2_common.launch import ReplaceString, RewrittenYaml


# setup.py 只安装 config/*.yaml，.rviz 不会进 install；
# realpath 解开 --symlink-install 的软链，回到源码树取配置。
# setup.py installs only config/*.yaml; realpath resolves back to the source tree.
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CONFIG_DIR = os.path.normpath(os.path.join(THIS_DIR, "..", "config"))


def generate_launch_description():
    params_file = LaunchConfiguration("params_file")
    openvins_config_path = LaunchConfiguration("openvins_config_path")
    namespace = LaunchConfiguration("namespace")
    use_sim_time = LaunchConfiguration("use_sim_time")
    log_level = LaunchConfiguration("log_level")

    frame_id = LaunchConfiguration("frame_id")
    odom_frame_id = LaunchConfiguration("odom_frame_id")
    map_frame_id = LaunchConfiguration("map_frame_id")
    publish_odom_tf = LaunchConfiguration("publish_odom_tf")
    publish_map_tf = LaunchConfiguration("publish_map_tf")
    planar_mode = LaunchConfiguration("planar_mode")
    localization = LaunchConfiguration("localization")

    left_image_topic = LaunchConfiguration("left_image_topic")
    right_image_topic = LaunchConfiguration("right_image_topic")
    left_info_topic = LaunchConfiguration("left_info_topic")
    right_info_topic = LaunchConfiguration("right_info_topic")
    odom_left_image_topic = LaunchConfiguration("odom_left_image_topic")
    odom_right_image_topic = LaunchConfiguration("odom_right_image_topic")
    odom_left_info_topic = LaunchConfiguration("odom_left_info_topic")
    odom_right_info_topic = LaunchConfiguration("odom_right_info_topic")
    odom_images_already_rectified = LaunchConfiguration(
        "odom_images_already_rectified")
    imu_topic = LaunchConfiguration("imu_topic")
    orientation_imu_topic = LaunchConfiguration("orientation_imu_topic")
    odom_topic = LaunchConfiguration("odom_topic")
    odom_info_topic = LaunchConfiguration("odom_info_topic")
    map_topic = LaunchConfiguration("map_topic")
    local_grid_obstacle_topic = LaunchConfiguration(
        "local_grid_obstacle_topic")
    local_grid_ground_topic = LaunchConfiguration("local_grid_ground_topic")

    database_path = LaunchConfiguration("database_path")
    delete_db_on_start = LaunchConfiguration("delete_db_on_start")
    launch_viz = LaunchConfiguration("launch_viz")
    rviz = LaunchConfiguration("rviz")
    rviz_cfg = LaunchConfiguration("rviz_cfg")

    navigation = LaunchConfiguration("navigation")
    nav2_params_file = LaunchConfiguration("nav2_params_file")
    nav2_startup_delay = LaunchConfiguration("nav2_startup_delay")
    nav2_autostart = LaunchConfiguration("nav2_autostart")
    nav2_use_composition = LaunchConfiguration("nav2_use_composition")
    use_keepout_zones = LaunchConfiguration("use_keepout_zones")
    keepout_mask = LaunchConfiguration("keepout_mask")

    publish_base_tf = LaunchConfiguration("publish_base_tf")

    declared_arguments = [
        DeclareLaunchArgument(
            "namespace", default_value="", description="ROS2 namespace。"),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="是否使用仿真时间。",
        ),
        DeclareLaunchArgument(
            "log_level", default_value="info", description="节点日志等级。"),
        DeclareLaunchArgument(
            "params_file",
            default_value=os.path.join(
                DEFAULT_CONFIG_DIR, "d435i_camera_imu_rtabmap.yaml"),
            description="RTAB-Map + OpenVINS 参数文件。",
        ),
        DeclareLaunchArgument(
            "openvins_config_path",
            default_value="",
            description=(
                "可选：OpenVINS 原生 yaml。非空时会覆盖 "
                "OdomOpenVINS/* 中同名参数。"
            ),
        ),
        DeclareLaunchArgument(
            "frame_id",
            default_value="camera_link",
            description=(
                "机器人基坐标系。相机单独使用时保持 camera_link；"
                "装到移动底盘上传入底盘的机体坐标系。"
            ),
        ),
        DeclareLaunchArgument(
            "odom_frame_id",
            default_value="odom",
            description="局部里程计坐标系。",
        ),
        DeclareLaunchArgument(
            "map_frame_id",
            default_value="map",
            description="全局地图坐标系。",
        ),
        DeclareLaunchArgument(
            "publish_odom_tf",
            default_value="true",
            description="是否由 OpenVINS 发布 odom 到机体的 TF。",
        ),
        DeclareLaunchArgument(
            "publish_map_tf",
            default_value="true",
            description="是否由 RTAB-Map 发布 map 到 odom 的 TF。",
        ),
        DeclareLaunchArgument(
            "planar_mode",
            default_value="false",
            description=(
                "true 时将里程计和地图限制为 x/y/yaw；"
                "默认 false 保留纯相机惯性的 6DoF 运动。"
            ),
        ),
        DeclareLaunchArgument(
            "localization",
            default_value="false",
            description="false 为建图，true 为使用已有数据库重定位。",
        ),
        DeclareLaunchArgument(
            "left_image_topic",
            default_value="/camera/camera/infra1/image_rect_raw",
            description="D435i 驱动原生左红外矫正图像话题。",
        ),
        DeclareLaunchArgument(
            "right_image_topic",
            default_value="/camera/camera/infra2/image_rect_raw",
            description="D435i 驱动原生右红外矫正图像话题。",
        ),
        DeclareLaunchArgument(
            "left_info_topic",
            default_value="/camera/camera/infra1/camera_info",
            description="D435i 驱动原生左红外 CameraInfo 话题。",
        ),
        DeclareLaunchArgument(
            "right_info_topic",
            default_value="/camera/camera/infra2/camera_info",
            description="D435i 驱动原生右红外 CameraInfo 话题。",
        ),
        DeclareLaunchArgument(
            "odom_left_image_topic",
            default_value=left_image_topic,
            description="OpenVINS 左目图像话题；默认与建图话题一致。",
        ),
        DeclareLaunchArgument(
            "odom_right_image_topic",
            default_value=right_image_topic,
            description="OpenVINS 右目图像话题；默认与建图话题一致。",
        ),
        DeclareLaunchArgument(
            "odom_left_info_topic",
            default_value=left_info_topic,
            description="OpenVINS 左目 CameraInfo。",
        ),
        DeclareLaunchArgument(
            "odom_right_info_topic",
            default_value=right_info_topic,
            description=(
                "OpenVINS 右目 CameraInfo。驱动未给出基线时，"
                "改传 d435i_extrinsics_relay 重写后的话题。"
            ),
        ),
        DeclareLaunchArgument(
            "odom_images_already_rectified",
            default_value="true",
            description=(
                "OpenVINS 输入是否已矫正；D435i 的 image_rect_raw 出厂已矫正。"
            ),
        ),
        DeclareLaunchArgument(
            "imu_topic",
            default_value="/camera/camera/imu",
            description=(
                "D435i 内置 IMU 合并话题，需驱动启用 unite_imu_method。"
            ),
        ),
        DeclareLaunchArgument(
            "orientation_imu_topic",
            default_value="/rtabmap/unused_orientation_imu",
            description=(
                "RTAB-Map 可选的姿态 IMU；D435i 原始 IMU 不含 orientation，"
                "默认保持为未发布话题。"
            ),
        ),
        DeclareLaunchArgument(
            "odom_topic",
            default_value="/odom",
            description="OpenVINS 输出里程计话题。",
        ),
        DeclareLaunchArgument(
            "odom_info_topic",
            default_value="/odom_info",
            description=(
                "OpenVINS odometry info 话题，"
                "RTAB-Map 用它读取特征/内点统计。"
            ),
        ),
        DeclareLaunchArgument(
            "map_topic",
            default_value="map",
            description="RTAB-Map 输出地图话题。",
        ),
        DeclareLaunchArgument(
            "local_grid_obstacle_topic",
            default_value="/local_grid_obstacle",
            description="RTAB-Map 输出局部障碍物点云话题。",
        ),
        DeclareLaunchArgument(
            "local_grid_ground_topic",
            default_value="/local_grid_ground",
            description="RTAB-Map 输出局部地面点云话题。",
        ),
        DeclareLaunchArgument(
            "database_path",
            default_value=os.path.expanduser(
                "~/.ros/rtabmap_d435i_camera_imu.db"),
            description="RTAB-Map 数据库路径。",
        ),
        DeclareLaunchArgument(
            "delete_db_on_start",
            default_value="true",
            description="启动时是否删除旧地图。",
        ),
        DeclareLaunchArgument(
            "launch_viz",
            default_value="true",
            description="是否启动 rtabmap_viz。",
        ),
        DeclareLaunchArgument(
            "rviz",
            default_value="false",
            description="是否启动 rviz2。",
        ),
        DeclareLaunchArgument(
            "rviz_cfg",
            default_value=os.path.join(
                DEFAULT_CONFIG_DIR, "d435i_camera_imu.rviz"),
            description="rviz2 配置文件。",
        ),
        DeclareLaunchArgument(
            "publish_base_tf",
            default_value="false",
            description=(
                "是否发布 frame_id 到相机的静态 TF。手持时保持 false；"
                "装到载体上且载体不发布该 TF 时设为 true。"
            ),
        ),
        DeclareLaunchArgument(
            "navigation",
            default_value="false",
            description="是否启动 Nav2。",
        ),
        DeclareLaunchArgument(
            "nav2_params_file",
            default_value=os.path.join(DEFAULT_CONFIG_DIR, "go2_nav2.yaml"),
            description=(
                "Nav2 参数文件。当前复用 GO2 的配置，footprint 与速度限幅"
                "仍是四足的取值，待按底盘实测替换。"
            ),
        ),
        DeclareLaunchArgument(
            "nav2_startup_delay",
            default_value="8.0",
            description="等待 RTAB-Map 建立 map 坐标系的时间，单位秒。",
        ),
        DeclareLaunchArgument(
            "nav2_autostart",
            default_value="true",
            description="Nav2 生命周期节点是否自动激活。",
        ),
        DeclareLaunchArgument(
            "nav2_use_composition",
            default_value="False",
            description=(
                "Humble 的 navigation_launch.py 用 PythonExpression 解析该值，"
                "需使用 True/False 首字母大写。"
            ),
        ),
        DeclareLaunchArgument(
            "use_keepout_zones",
            default_value="false",
            description="是否启用 Nav2 KeepoutFilter 禁行区。",
        ),
        DeclareLaunchArgument(
            "keepout_mask",
            default_value=os.path.expanduser("~/.ros/keepout_mask.yaml"),
            description=(
                "Keepout mask 的 YAML 文件路径；默认使用 ~/.ros/keepout_mask.yaml，"
                "其 PGM 与 YAML 应保持和原始地图相同的尺寸、分辨率和原点。"
            ),
        ),
    ]

    # 相机与 IMU 的外参由 RealSense 驱动的静态 TF 提供。
    # Camera-IMU extrinsics come from the RealSense driver's static TF.
    # 装到载体上时补一条机体到相机的静态 TF，使整条链在本机内闭合。
    # Mounted mode adds body-to-camera so the whole chain stays on this host.
    base_to_camera_tf = Node(
        condition=IfCondition(publish_base_tf),
        package="tf2_ros",
        executable="static_transform_publisher",
        name="base_to_camera_tf",
        output="screen",
        arguments=[
            "--x", "0.19891",
            "--y", "0.0",
            "--z", "0.22928",
            "--roll", "0.0",
            "--pitch", "0.0",
            "--yaw", "0.0",
            "--frame-id", frame_id,
            "--child-frame-id", "camera_link",
        ],
    )

    openvins_odometry_node = Node(
        package="rtabmap_odom",
        executable="stereo_odometry",
        name="openvins_stereo_odometry",
        namespace=namespace,
        output="screen",
        parameters=[
            params_file,
            {
                "use_sim_time": use_sim_time,
                "frame_id": frame_id,
                "odom_frame_id": odom_frame_id,
                "publish_tf": ParameterValue(
                    publish_odom_tf, value_type=bool),
                "OdomOpenVINS/ConfigPath": openvins_config_path,
                # RTAB-Map core 参数在 ROS 2 中按字符串传递。
                "Reg/Force3DoF": ParameterValue(
                    planar_mode, value_type=str),
                "Rtabmap/ImagesAlreadyRectified": ParameterValue(
                    odom_images_already_rectified, value_type=str),
            },
        ],
        remappings=[
            ("left/image_rect", odom_left_image_topic),
            ("right/image_rect", odom_right_image_topic),
            ("left/camera_info", odom_left_info_topic),
            ("right/camera_info", odom_right_info_topic),
            ("imu", imu_topic),
            ("odom", odom_topic),
            ("odom_info", odom_info_topic),
        ],
        arguments=["--ros-args", "--log-level", log_level],
    )

    rtabmap_common_parameters = [
        params_file,
        {
            "use_sim_time": use_sim_time,
            "frame_id": frame_id,
            "odom_frame_id": odom_frame_id,
            "map_frame_id": map_frame_id,
            "publish_tf": ParameterValue(publish_map_tf, value_type=bool),
            "database_path": database_path,
            "Reg/Force3DoF": ParameterValue(
                planar_mode, value_type=str),
        },
    ]
    rtabmap_remappings = [
        ("left/image_rect", left_image_topic),
        ("right/image_rect", right_image_topic),
        ("left/camera_info", left_info_topic),
        ("right/camera_info", right_info_topic),
        ("imu", orientation_imu_topic),
        ("odom", odom_topic),
        ("odom_info", odom_info_topic),
        ("map", map_topic),
        ("local_grid_obstacle", local_grid_obstacle_topic),
        ("local_grid_ground", local_grid_ground_topic),
    ]

    rtabmap_mapping_node = Node(
        condition=UnlessCondition(localization),
        package="rtabmap_slam",
        executable="rtabmap",
        name="rtabmap",
        namespace=namespace,
        output="screen",
        parameters=rtabmap_common_parameters + [{
            "delete_db_on_start": ParameterValue(
                delete_db_on_start, value_type=bool),
            "Mem/IncrementalMemory": "true",
            "Mem/InitWMWithAllNodes": "false",
            "Mem/LocalizationReadOnly": "false",
        }],
        remappings=rtabmap_remappings,
        arguments=["--ros-args", "--log-level", log_level],
    )

    # 重定位模式禁止删除数据库，并关闭增量记忆，避免增加新地图节点。
    rtabmap_localization_node = Node(
        condition=IfCondition(localization),
        package="rtabmap_slam",
        executable="rtabmap",
        name="rtabmap",
        namespace=namespace,
        output="screen",
        parameters=rtabmap_common_parameters + [{
            "delete_db_on_start": False,
            "Mem/IncrementalMemory": "false",
            "Mem/InitWMWithAllNodes": "true",
            "Mem/LocalizationReadOnly": "false",
        }],
        remappings=rtabmap_remappings,
        arguments=["--ros-args", "--log-level", log_level],
    )

    rtabmap_viz_node = Node(
        package="rtabmap_viz",
        executable="rtabmap_viz",
        name="rtabmap_viz",
        namespace=namespace,
        output="screen",
        condition=IfCondition(launch_viz),
        parameters=[
            params_file,
            {
                "use_sim_time": use_sim_time,
                "frame_id": frame_id,
                "odom_frame_id": odom_frame_id,
                "map_frame_id": map_frame_id,
            },
        ],
        remappings=rtabmap_remappings,
        arguments=["--ros-args", "--log-level", log_level],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        namespace=namespace,
        output="screen",
        condition=IfCondition(rviz),
        arguments=["-d", rviz_cfg],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    # go2_nav2.yaml 用占位符表达坐标系，用带 /rtabmap/ 前缀的栅格话题名。
    # 两者都在这里替换成本 launch 实际使用的值，yaml 无需修改。
    # Placeholders and grid topics in the Nav2 yaml are rewritten here.
    nav2_params_with_frames = ReplaceString(
        source_file=nav2_params_file,
        replacements={
            "GO2_MAP_FRAME": map_frame_id,
            "GO2_ODOM_FRAME": odom_frame_id,
            "/rtabmap/local_grid_obstacle": local_grid_obstacle_topic,
            "/rtabmap/local_grid_ground": local_grid_ground_topic,
            "KEEPOUT_ZONE_ENABLED": use_keepout_zones,
        },
    )
    rewritten_nav2_params = RewrittenYaml(
        source_file=nav2_params_with_frames,
        param_rewrites={
            "use_sim_time": use_sim_time,
            "robot_base_frame": frame_id,
            "odom_topic": odom_topic,
        },
        convert_types=True,
    )
    configured_nav2_params = ParameterFile(
        rewritten_nav2_params, allow_substs=True)

    nav2_container = Node(
        condition=IfCondition(nav2_use_composition),
        package="rclcpp_components",
        executable="component_container_isolated",
        name="nav2_container",
        output="screen",
        parameters=[
            configured_nav2_params,
            {"autostart": ParameterValue(nav2_autostart, value_type=bool)},
        ],
        arguments=["--ros-args", "--log-level", log_level],
        remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
    )
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("nav2_bringup"),
                "launch",
                "navigation_launch.py",
            )
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "params_file": rewritten_nav2_params,
            "autostart": nav2_autostart,
            "use_composition": nav2_use_composition,
            "container_name": "nav2_container",
            "log_level": log_level,
        }.items(),
    )

    # KeepoutFilter 按 Nav2 Humble 官方链路使用独立 mask map_server 和
    # costmap_filter_info_server；它们不会发布或替换 RTAB-Map 的 /map。
    keepout_mask_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="keepout_filter_mask_server",
        namespace=namespace,
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "yaml_filename": keepout_mask,
                "topic_name": "keepout_filter_mask",
                "frame_id": map_frame_id,
            }
        ],
        remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
        arguments=["--ros-args", "--log-level", log_level],
    )
    keepout_filter_info_server = Node(
        package="nav2_map_server",
        executable="costmap_filter_info_server",
        name="keepout_costmap_filter_info_server",
        namespace=namespace,
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "type": 0,
                "filter_info_topic": "/keepout_costmap_filter_info",
                "mask_topic": "/keepout_filter_mask",
                "base": 0.0,
                "multiplier": 1.0,
            }
        ],
        remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
        arguments=["--ros-args", "--log-level", log_level],
    )
    keepout_lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_keepout_zone",
        namespace=namespace,
        output="screen",
        parameters=[
            {
                "use_sim_time": use_sim_time,
                "autostart": ParameterValue(nav2_autostart, value_type=bool),
                "node_names": [
                    "keepout_filter_mask_server",
                    "keepout_costmap_filter_info_server",
                ],
            }
        ],
        arguments=["--ros-args", "--log-level", log_level],
    )
    keepout_nodes = GroupAction(
        condition=IfCondition(use_keepout_zones),
        actions=[
            keepout_mask_server,
            keepout_filter_info_server,
            keepout_lifecycle_manager,
        ],
    )
    delayed_nav2 = TimerAction(
        period=nav2_startup_delay,
        actions=[
            GroupAction(
                condition=IfCondition(navigation),
                actions=[nav2_container, nav2_launch, keepout_nodes],
            ),
        ],
    )

    return LaunchDescription(
        declared_arguments
        + [
            base_to_camera_tf,
            openvins_odometry_node,
            rtabmap_mapping_node,
            rtabmap_localization_node,
            rtabmap_viz_node,
            rviz_node,
            delayed_nav2,
        ]
    )
