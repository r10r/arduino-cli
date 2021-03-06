# This file is part of arduino-cli.
#
# Copyright 2020 ARDUINO SA (http://www.arduino.cc/)
#
# This software is released under the GNU General Public License version 3,
# which covers the main part of arduino-cli.
# The terms of this license can be found at:
# https://www.gnu.org/licenses/gpl-3.0.en.html
#
# You can be released from the requirements of the above licenses by purchasing
# a commercial license. Buying such a license is mandatory if you want to modify or
# otherwise use the software for commercial activities involving the Arduino
# software without disclosing the source code of your own applications. To purchase
# a commercial license, send an email to license@arduino.cc.
import platform

import simplejson as json
import pytest
from git import Repo
from pathlib import Path


def test_list(run_command):
    # Init the environment explicitly
    run_command("core update-index")

    # When output is empty, nothing is printed out, no matter the output format
    result = run_command("lib list")
    assert result.ok
    assert "" == result.stderr
    assert "No libraries installed." == result.stdout.strip()
    result = run_command("lib list --format json")
    assert result.ok
    assert "" == result.stderr
    assert 0 == len(json.loads(result.stdout))

    # Install something we can list at a version older than latest
    result = run_command("lib install ArduinoJson@6.11.0")
    assert result.ok

    # Look at the plain text output
    result = run_command("lib list")
    assert result.ok
    assert "" == result.stderr
    lines = result.stdout.strip().splitlines()
    assert 2 == len(lines)
    toks = [t.strip() for t in lines[1].split(maxsplit=4)]
    # Verifies the expected number of field
    assert 5 == len(toks)
    # be sure line contain the current version AND the available version
    assert "" != toks[1]
    assert "" != toks[2]
    # Verifies library sentence
    assert "An efficient and elegant JSON library..." == toks[4]

    # Look at the JSON output
    result = run_command("lib list --format json")
    assert result.ok
    assert "" == result.stderr
    data = json.loads(result.stdout)
    assert 1 == len(data)
    # be sure data contains the available version
    assert "" != data[0]["release"]["version"]

    # Install something we can list without provides_includes field given in library.properties
    result = run_command("lib install Arduino_APDS9960@1.0.3")
    assert result.ok
    # Look at the JSON output
    result = run_command("lib list Arduino_APDS9960 --format json")
    assert result.ok
    assert "" == result.stderr
    data = json.loads(result.stdout)
    assert 1 == len(data)
    # be sure data contains the correct provides_includes field
    assert "Arduino_APDS9960.h" == data[0]["library"]["provides_includes"][0]


def test_list_exit_code(run_command):
    # Init the environment explicitly
    assert run_command("core update-index")

    assert run_command("core list")

    # Verifies lib list doesn't fail when platform is not specified
    result = run_command("lib list")
    assert result.ok
    assert result.stderr.strip() == ""

    # Verify lib list command fails because specified platform is not installed
    result = run_command("lib list -b arduino:samd:mkr1000")
    assert result.failed
    assert (
        result.stderr.strip() == "Error listing Libraries: loading board data: platform arduino:samd is not installed"
    )

    assert run_command('lib install "AllThingsTalk LoRaWAN SDK"')

    # Verifies lib list command keeps failing
    result = run_command("lib list -b arduino:samd:mkr1000")
    assert result.failed
    assert (
        result.stderr.strip() == "Error listing Libraries: loading board data: platform arduino:samd is not installed"
    )

    assert run_command("core install arduino:samd")

    # Verifies lib list command now works since platform has been installed
    result = run_command("lib list -b arduino:samd:mkr1000")
    assert result.ok
    assert result.stderr.strip() == ""


def test_list_with_fqbn(run_command):
    # Init the environment explicitly
    assert run_command("core update-index")

    # Install core
    assert run_command("core install arduino:avr")

    # Install some library
    assert run_command("lib install ArduinoJson")
    assert run_command("lib install wm8978-esp32")

    # Look at the plain text output
    result = run_command("lib list -b arduino:avr:uno")
    assert result.ok
    assert "" == result.stderr
    lines = result.stdout.strip().splitlines()
    assert 2 == len(lines)

    # Verifies library is compatible
    toks = [t.strip() for t in lines[1].split(maxsplit=4)]
    assert 5 == len(toks)
    assert "ArduinoJson" == toks[0]

    # Look at the JSON output
    result = run_command("lib list -b arduino:avr:uno --format json")
    assert result.ok
    assert "" == result.stderr
    data = json.loads(result.stdout)
    assert 1 == len(data)

    # Verifies library is compatible
    assert data[0]["library"]["name"] == "ArduinoJson"
    assert data[0]["library"]["compatible_with"]["arduino:avr:uno"]


def test_list_provides_includes_fallback(run_command):
    # Verifies "provides_includes" field is returned even if libraries don't declare
    # the "includes" property in their "library.properties" file
    assert run_command("update")

    # Install core
    assert run_command("core install arduino:avr@1.8.3")
    assert run_command("lib install ArduinoJson@6.17.2")

    # List all libraries, even the ones installed with the above core
    result = run_command("lib list --all --fqbn arduino:avr:uno --format json")
    assert result.ok
    assert "" == result.stderr

    data = json.loads(result.stdout)
    assert 6 == len(data)

    libs = {l["library"]["name"]: l["library"]["provides_includes"] for l in data}
    assert ["SoftwareSerial.h"] == libs["SoftwareSerial"]
    assert ["Wire.h"] == libs["Wire"]
    assert ["EEPROM.h"] == libs["EEPROM"]
    assert ["HID.h"] == libs["HID"]
    assert ["SPI.h"] == libs["SPI"]
    assert ["ArduinoJson.h", "ArduinoJson.hpp"] == libs["ArduinoJson"]


def test_lib_download(run_command, downloads_dir):

    # Download a specific lib version
    assert run_command("lib download AudioZero@1.0.0")
    assert Path(downloads_dir, "libraries", "AudioZero-1.0.0.zip").exists()

    # Wrong lib version
    result = run_command("lib download AudioZero@69.42.0")
    assert result.failed

    # Wrong lib
    result = run_command("lib download AudioZ")
    assert result.failed


def test_install(run_command):
    libs = ['"AzureIoTProtocol_MQTT"', '"CMMC MQTT Connector"', '"WiFiNINA"']
    # Should be safe to run install multiple times
    assert run_command("lib install {}".format(" ".join(libs)))
    assert run_command("lib install {}".format(" ".join(libs)))

    # Test failing-install of library with wrong dependency
    # (https://github.com/arduino/arduino-cli/issues/534)
    result = run_command("lib install MD_Parola@3.2.0")
    assert "Error resolving dependencies for MD_Parola@3.2.0: dependency 'MD_MAX72xx' is not available" in result.stderr


def test_install_git_url_and_zip_path_flags_visibility(run_command, data_dir, downloads_dir):
    # Verifies installation fail because flags are not found
    git_url = "https://github.com/arduino-libraries/WiFi101.git"
    res = run_command(f"lib install --git-url {git_url}")
    assert res.failed
    assert "--git-url and --zip-path are disabled by default, for more information see:" in res.stderr

    assert run_command("lib download AudioZero@1.0.0")
    zip_path = Path(downloads_dir, "libraries", "AudioZero-1.0.0.zip")
    res = run_command(f"lib install --zip-path {zip_path}")
    assert res.failed
    assert "--git-url and --zip-path are disabled by default, for more information see:" in res.stderr

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }
    # Verifies installation is successful when flags are enabled with env var
    res = run_command(f"lib install --git-url {git_url}", custom_env=env)
    assert res.ok
    assert "--git-url and --zip-path flags allow installing untrusted files, use it at your own risk." in res.stdout

    res = run_command(f"lib install --zip-path {zip_path}", custom_env=env)
    assert res.ok
    assert "--git-url and --zip-path flags allow installing untrusted files, use it at your own risk." in res.stdout

    # Uninstall libraries to install them again
    assert run_command("lib uninstall WiFi101 AudioZero")

    # Verifies installation is successful when flags are enabled with settings file
    assert run_command("config init --dest-dir .", custom_env=env)

    res = run_command(f"lib install --git-url {git_url}")
    assert res.ok
    assert "--git-url and --zip-path flags allow installing untrusted files, use it at your own risk." in res.stdout

    res = run_command(f"lib install --zip-path {zip_path}")
    assert res.ok
    assert "--git-url and --zip-path flags allow installing untrusted files, use it at your own risk." in res.stdout


def test_install_with_git_url(run_command, data_dir, downloads_dir):
    # Initialize configs to enable --git-url flag
    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }
    assert run_command("config init --dest-dir .", custom_env=env)

    lib_install_dir = Path(data_dir, "libraries", "WiFi101")
    # Verifies library is not already installed
    assert not lib_install_dir.exists()

    git_url = "https://github.com/arduino-libraries/WiFi101.git"

    # Test git-url library install
    res = run_command(f"lib install --git-url {git_url}")
    assert res.ok
    assert "--git-url and --zip-path flags allow installing untrusted files, use it at your own risk." in res.stdout

    # Verifies library is installed in expected path
    assert lib_install_dir.exists()

    # Reinstall library
    assert run_command(f"lib install --git-url {git_url}")

    # Verifies library remains installed
    assert lib_install_dir.exists()


def test_install_with_zip_path(run_command, data_dir, downloads_dir):
    # Initialize configs to enable --zip-path flag
    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }
    assert run_command("config init --dest-dir .", custom_env=env)

    # Download a specific lib version
    assert run_command("lib download AudioZero@1.0.0")

    lib_install_dir = Path(data_dir, "libraries", "AudioZero-1.0.0")
    # Verifies library is not already installed
    assert not lib_install_dir.exists()

    zip_path = Path(downloads_dir, "libraries", "AudioZero-1.0.0.zip")
    # Test zip-path install
    res = run_command(f"lib install --zip-path {zip_path}")
    assert res.ok
    assert "--git-url and --zip-path flags allow installing untrusted files, use it at your own risk." in res.stdout

    # Verifies library is installed in expected path
    assert lib_install_dir.exists()
    files = list(lib_install_dir.glob("**/*"))
    assert lib_install_dir / "examples" / "SimpleAudioPlayerZero" / "SimpleAudioPlayerZero.ino" in files
    assert lib_install_dir / "src" / "AudioZero.h" in files
    assert lib_install_dir / "src" / "AudioZero.cpp" in files
    assert lib_install_dir / "keywords.txt" in files
    assert lib_install_dir / "library.properties" in files
    assert lib_install_dir / "README.adoc" in files

    # Reinstall library
    assert run_command(f"lib install --zip-path {zip_path}")

    # Verifies library remains installed
    assert lib_install_dir.exists()
    files = list(lib_install_dir.glob("**/*"))
    assert lib_install_dir / "examples" / "SimpleAudioPlayerZero" / "SimpleAudioPlayerZero.ino" in files
    assert lib_install_dir / "src" / "AudioZero.h" in files
    assert lib_install_dir / "src" / "AudioZero.cpp" in files
    assert lib_install_dir / "keywords.txt" in files
    assert lib_install_dir / "library.properties" in files
    assert lib_install_dir / "README.adoc" in files


def test_update_index(run_command):
    result = run_command("lib update-index")
    assert result.ok
    assert "Updating index: library_index.json downloaded" == result.stdout.splitlines()[-1].strip()


def test_uninstall(run_command):
    libs = ['"AzureIoTProtocol_MQTT"', '"WiFiNINA"']
    assert run_command("lib install {}".format(" ".join(libs)))

    result = run_command("lib uninstall {}".format(" ".join(libs)))
    assert result.ok


def test_uninstall_spaces(run_command):
    key = '"LiquidCrystal I2C"'
    assert run_command("lib install {}".format(key))
    assert run_command("lib uninstall {}".format(key))
    result = run_command("lib list --format json")
    assert result.ok
    assert len(json.loads(result.stdout)) == 0


def test_lib_ops_caseinsensitive(run_command):
    """
    This test is supposed to (un)install the following library,
    As you can see the name is all caps:

    Name: "PCM"
      Author: David Mellis <d.mellis@bcmi-labs.cc>, Michael Smith <michael@hurts.ca>
      Maintainer: David Mellis <d.mellis@bcmi-labs.cc>
      Sentence: Playback of short audio samples.
      Paragraph: These samples are encoded directly in the Arduino sketch as an array of numbers.
      Website: http://highlowtech.org/?p=1963
      Category: Signal Input/Output
      Architecture: avr
      Types: Contributed
      Versions: [1.0.0]
    """
    key = "pcm"
    assert run_command("lib install {}".format(key))
    assert run_command("lib uninstall {}".format(key))
    result = run_command("lib list --format json")
    assert result.ok
    assert len(json.loads(result.stdout)) == 0


def test_search(run_command):
    assert run_command("lib update-index")

    result = run_command("lib search --names")
    assert result.ok
    lines = [l.strip() for l in result.stdout.strip().splitlines()]
    assert "Updating index: library_index.json downloaded" in lines
    libs = [l[6:].strip('"') for l in lines if "Name:" in l]

    expected = {"WiFi101", "WiFi101OTA", "Firebase Arduino based on WiFi101"}
    assert expected == {lib for lib in libs if "WiFi101" in lib}

    result = run_command("lib search --names --format json")
    assert result.ok
    libs_json = json.loads(result.stdout)
    assert len(libs) == len(libs_json.get("libraries"))

    result = run_command("lib search")
    assert result.ok

    # Search for a specific target
    result = run_command("lib search ArduinoJson --format json")
    assert result.ok
    libs_json = json.loads(result.stdout)
    assert len(libs_json.get("libraries")) >= 1


def test_search_paragraph(run_command):
    """
    Search for a string that's only present in the `paragraph` field
    within the index file.
    """
    assert run_command("lib update-index")
    result = run_command('lib search "A simple and efficient JSON library" --format json')
    assert result.ok
    libs_json = json.loads(result.stdout)
    assert 1 == len(libs_json.get("libraries"))


def test_lib_list_with_updatable_flag(run_command):
    # Init the environment explicitly
    run_command("lib update-index")

    # No libraries to update
    result = run_command("lib list --updatable")
    assert result.ok
    assert "" == result.stderr
    assert "No updates available." == result.stdout.strip()
    # No library to update in json
    result = run_command("lib list --updatable --format json")
    assert result.ok
    assert "" == result.stderr
    assert 0 == len(json.loads(result.stdout))

    # Install outdated library
    assert run_command("lib install ArduinoJson@6.11.0")
    # Install latest version of library
    assert run_command("lib install WiFi101")

    res = run_command("lib list --updatable")
    assert res.ok
    assert "" == res.stderr
    # lines = res.stdout.strip().splitlines()
    lines = [l.strip().split(maxsplit=4) for l in res.stdout.strip().splitlines()]
    assert 2 == len(lines)
    assert ["Name", "Installed", "Available", "Location", "Description"] in lines
    line = lines[1]
    assert "ArduinoJson" == line[0]
    assert "6.11.0" == line[1]
    # Verifies available version is not equal to installed one and not empty
    assert "6.11.0" != line[2]
    assert "" != line[2]
    assert "An efficient and elegant JSON library..." == line[4]

    # Look at the JSON output
    res = run_command("lib list --updatable --format json")
    assert res.ok
    assert "" == res.stderr
    data = json.loads(res.stdout)
    assert 1 == len(data)
    # be sure data contains the available version
    assert "6.11.0" == data[0]["library"]["version"]
    assert "6.11.0" != data[0]["release"]["version"]
    assert "" != data[0]["release"]["version"]


def test_install_with_git_url_from_current_directory(run_command, downloads_dir, data_dir):
    assert run_command("update")

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }

    lib_install_dir = Path(data_dir, "libraries", "WiFi101")
    # Verifies library is not installed
    assert not lib_install_dir.exists()

    # Clone repository locally
    git_url = "https://github.com/arduino-libraries/WiFi101.git"
    repo_dir = Path(data_dir, "WiFi101")
    assert Repo.clone_from(git_url, repo_dir)

    assert run_command("lib install --git-url .", custom_working_dir=repo_dir, custom_env=env)

    # Verifies library is installed to correct folder
    assert lib_install_dir.exists()


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Using a file uri as git url doesn't work on Windows, "
    + "this must be removed when this issue is fixed: https://github.com/go-git/go-git/issues/247",
)
def test_install_with_git_url_local_file_uri(run_command, downloads_dir, data_dir):
    assert run_command("update")

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }

    lib_install_dir = Path(data_dir, "libraries", "WiFi101")
    # Verifies library is not installed
    assert not lib_install_dir.exists()

    # Clone repository locally
    git_url = "https://github.com/arduino-libraries/WiFi101.git"
    repo_dir = Path(data_dir, "WiFi101")
    assert Repo.clone_from(git_url, repo_dir)

    assert run_command(f"lib install --git-url {repo_dir.as_uri()}", custom_env=env)

    # Verifies library is installed
    assert lib_install_dir.exists()


def test_install_with_git_local_url(run_command, downloads_dir, data_dir):
    assert run_command("update")

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }

    lib_install_dir = Path(data_dir, "libraries", "WiFi101")
    # Verifies library is not installed
    assert not lib_install_dir.exists()

    # Clone repository locally
    git_url = "https://github.com/arduino-libraries/WiFi101.git"
    repo_dir = Path(data_dir, "WiFi101")
    assert Repo.clone_from(git_url, repo_dir)

    assert run_command(f"lib install --git-url {repo_dir}", custom_env=env)

    # Verifies library is installed
    assert lib_install_dir.exists()


def test_install_with_git_url_relative_path(run_command, downloads_dir, data_dir):
    assert run_command("update")

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }

    lib_install_dir = Path(data_dir, "libraries", "WiFi101")
    # Verifies library is not installed
    assert not lib_install_dir.exists()

    # Clone repository locally
    git_url = "https://github.com/arduino-libraries/WiFi101.git"
    repo_dir = Path(data_dir, "WiFi101")
    assert Repo.clone_from(git_url, repo_dir)

    assert run_command("lib install --git-url ./WiFi101", custom_working_dir=data_dir, custom_env=env)

    # Verifies library is installed
    assert lib_install_dir.exists()


def test_install_with_git_url_does_not_create_git_repo(run_command, downloads_dir, data_dir):
    assert run_command("update")

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }

    lib_install_dir = Path(data_dir, "libraries", "WiFi101")
    # Verifies library is not installed
    assert not lib_install_dir.exists()

    # Clone repository locally
    git_url = "https://github.com/arduino-libraries/WiFi101.git"
    repo_dir = Path(data_dir, "WiFi101")
    assert Repo.clone_from(git_url, repo_dir)

    assert run_command(f"lib install --git-url {repo_dir}", custom_env=env)

    # Verifies installed library is not a git repository
    assert not Path(lib_install_dir, ".git").exists()


def test_install_with_git_url_multiple_libraries(run_command, downloads_dir, data_dir):
    assert run_command("update")

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }

    wifi_install_dir = Path(data_dir, "libraries", "WiFi101")
    ble_install_dir = Path(data_dir, "libraries", "ArduinoBLE")
    # Verifies libraries are not installed
    assert not wifi_install_dir.exists()
    assert not ble_install_dir.exists()

    wifi_url = "https://github.com/arduino-libraries/WiFi101.git"
    ble_url = "https://github.com/arduino-libraries/ArduinoBLE.git"

    assert run_command(f"lib install --git-url {wifi_url} {ble_url}", custom_env=env)

    # Verifies library are installed
    assert wifi_install_dir.exists()
    assert ble_install_dir.exists()


def test_install_with_zip_path_multiple_libraries(run_command, downloads_dir, data_dir):
    assert run_command("update")

    env = {
        "ARDUINO_DATA_DIR": data_dir,
        "ARDUINO_DOWNLOADS_DIR": downloads_dir,
        "ARDUINO_SKETCHBOOK_DIR": data_dir,
        "ARDUINO_ENABLE_UNSAFE_LIBRARY_INSTALL": "true",
    }

    # Downloads zip to be installed later
    assert run_command("lib download WiFi101@0.16.1")
    assert run_command("lib download ArduinoBLE@1.1.3")
    wifi_zip_path = Path(downloads_dir, "libraries", "WiFi101-0.16.1.zip")
    ble_zip_path = Path(downloads_dir, "libraries", "ArduinoBLE-1.1.3.zip")

    wifi_install_dir = Path(data_dir, "libraries", "WiFi101-0.16.1")
    ble_install_dir = Path(data_dir, "libraries", "ArduinoBLE-1.1.3")
    # Verifies libraries are not installed
    assert not wifi_install_dir.exists()
    assert not ble_install_dir.exists()

    assert run_command(f"lib install --zip-path {wifi_zip_path} {ble_zip_path}", custom_env=env)

    # Verifies library are installed
    assert wifi_install_dir.exists()
    assert ble_install_dir.exists()


def test_lib_examples(run_command, data_dir):
    assert run_command("update")

    assert run_command("lib install Arduino_JSON@0.1.0")

    res = run_command("lib examples Arduino_JSON --format json")
    assert res.ok
    data = json.loads(res.stdout)
    assert len(data) == 1
    examples = data[0]["examples"]

    assert str(Path(data_dir, "libraries", "Arduino_JSON", "examples", "JSONArray")) in examples
    assert str(Path(data_dir, "libraries", "Arduino_JSON", "examples", "JSONKitchenSink")) in examples
    assert str(Path(data_dir, "libraries", "Arduino_JSON", "examples", "JSONObject")) in examples


def test_lib_examples_with_pde_file(run_command, data_dir):
    assert run_command("update")

    assert run_command("lib install Encoder@1.4.1")

    res = run_command("lib examples Encoder --format json")
    assert res.ok
    data = json.loads(res.stdout)
    assert len(data) == 1
    examples = data[0]["examples"]

    assert str(Path(data_dir, "libraries", "Encoder", "examples", "Basic")) in examples
    assert str(Path(data_dir, "libraries", "Encoder", "examples", "NoInterrupts")) in examples
    assert str(Path(data_dir, "libraries", "Encoder", "examples", "SpeedTest")) in examples
    assert str(Path(data_dir, "libraries", "Encoder", "examples", "TwoKnobs")) in examples
