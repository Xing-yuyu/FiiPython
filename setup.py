from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="FiiPython",
    version="1.0.0",
    author="FII Team",
    author_email="your.email@example.com",
    description="FII无人机仿真系统 - 解析FII文件并生成无人机运动视频",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/FiiPython",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pylint>=2.17.0",
            "black>=23.0.0",
        ],
        "audio": [
            "ffmpeg-python>=0.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fiipython-simulate=scripts.run_simulation:main",
            "fiipython-show=scripts.show:main",
        ],
    },
    include_package_data=True,
    package_data={
        "FiiPython": ["py.typed"],
    },
)