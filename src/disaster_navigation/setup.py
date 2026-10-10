from glob import glob
import os
from setuptools import find_packages, setup

package_name = 'disaster_navigation'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        (
            os.path.join('share', package_name),
            ['package.xml'],
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py'),
        ),
        (
            os.path.join('share', package_name, 'config'),
            glob('config/*.yaml'),
        ),
        (
            os.path.join('share', package_name, 'maps'),
            glob('maps/*'),
        ),
        (
            os.path.join('share', package_name, 'worlds'),
            glob('worlds/*.sdf'),
        ),
        (
            os.path.join('share', package_name, 'models', 'reference_ugv'),
            glob('models/reference_ugv/*'),
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='bhavana-malladi',
    maintainer_email='bhavana-malladi@todo.todo',
    description='Navigation package for disaster search and rescue simulation',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'navigation_node = disaster_navigation.navigation_node:main',
        ],
    },
)
