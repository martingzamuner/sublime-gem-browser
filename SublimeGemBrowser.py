import os
import os.path
import sublime
import sublime_plugin
import subprocess
import pipes
import re
import sys
import inspect
import webbrowser
import locale
import json

PLUGIN_PATH = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))

class ListGemsCommand(sublime_plugin.WindowCommand):
    """
    A command that shows a list of all installed gems (by bundle list command)
    """

    def run(self):
        self.app_path_mac = None
        self.get_gem_list()
        if self.gems != None:
          self.show_gem_list()

    def show_gem_list(self):
        gem_labels = [[ '%s %s' % (gem["name"],  gem["version"]), gem["summary"]] for gem in self.gems]
        self.window.show_quick_panel(gem_labels, self.show_gem_menu)

    def show_gem_menu(self, gem_index):
        if gem_index == -1:
            return
        self.gem = self.gems[gem_index]
        self.gem["rubygems_url"] = 'https://rubygems.org/gems/%s/versions/%s' % (self.gem["name"], self.gem["version"])
        self.gem["rubydocs_url"] = 'http://www.rubydoc.info/gems/%s/%s' % (self.gem["name"], self.gem["version"])
        self.gem["omniref_url"] = 'https://www.omniref.com/ruby/gems/%s/%s' % (self.gem["name"], self.gem["version"])

        self.gem_options = [
                ["Open gem folder in new editor window", self.gem["path"]],
                [ self.gem["name"] + " homepage", self.gem["homepage_url"]],
                ["Rubygems", self.gem["rubygems_url"]],
                ["Rubydocs", self.gem["rubydocs_url"]],
                ["Omniref", self.gem["omniref_url"]]
                ]

        sublime.set_timeout(lambda:
            self.window.show_quick_panel(self.gem_options, self.goto_result)
            ,10)

    def goto_result(self, option_index):
        param = self.gem_options[option_index][1]
        if option_index == 0:
            self.open_folder_in_new_window(param, self.gem['spec_path'])
        elif option_index >=1 and option_index <= 4:
            webbrowser.open(param)

    def get_gem_list(self):
        ruby_file = os.path.join(PLUGIN_PATH, "list_gems.rb")
        rvm_ruby = os.path.expanduser('~/.rvm/bin/rvm-auto-ruby')
        if os.path.isfile(rvm_ruby):
            ruby_executable = rvm_ruby
        else:
            rbenv_ruby = os.path.expanduser('~/.rbenv/shims/ruby')
            if os.path.isfile(rbenv_ruby):
                ruby_executable = rbenv_ruby
            else:
                ruby_executable = 'ruby'
        pipe = subprocess.Popen([ruby_executable, ruby_file],
            cwd=self.gemfile_folder() + '/rankia/',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )
        output, error = pipe.communicate()
        if pipe.returncode != 0:
            sublime.error_message("Failed to get list of gems: " + self._sanitize_output(error))
            self.gems = None
        else:
            self.gems = json.loads(self._sanitize_output(output))

    def _sanitize_output(self, output):
        return output.decode(locale.getpreferredencoding(), 'ignore').strip()

    def run_subprocess(self, command):
        current_path = pipes.quote(self.gemfile_folder())
        if current_path == None: return None
        command_with_cd = 'cd ' + current_path + ' && ' + command


    def gemfile_folder(self):
        folders = self.window.folders()
        if len(folders) > 0:
            return folders[0]
        else:
            view = self.window.active_view()
            if view:
                filename = view.file_name()
                if filename:
                    return os.path.dirname(filename)


    def open_folder_in_new_window(self, folder, file):
        if sublime.version() >= '3000':
            self.open_folder_in_new_window_ST3(folder, file)
        else:
            self.open_folder_in_new_window_ST2(folder, file)

    def open_folder_in_new_window_ST3(self, folder, file):
        sublime.run_command("new_window")
        sublime.active_window().set_project_data({"folders": [{"path": folder}]})

    def open_folder_in_new_window_ST2(self, folder, file):
        return subprocess.Popen([self.get_sublime_path(), '-n', folder])

    def get_sublime_path(self):
        if sublime.platform() == 'osx':
            if not self.app_path_mac:
                # taken from https://github.com/freewizard/SublimeGotoFolder/blob/master/GotoFolder.py:
                from ctypes import cdll, byref, Structure, c_int, c_char_p, c_void_p
                from ctypes.util import find_library
                Foundation = cdll.LoadLibrary(find_library('Foundation'))
                CFBundleGetMainBundle = Foundation.CFBundleGetMainBundle
                CFBundleGetMainBundle.restype = c_void_p
                bundle = CFBundleGetMainBundle()
                CFBundleCopyBundleURL = Foundation.CFBundleCopyBundleURL
                CFBundleCopyBundleURL.argtypes = [c_void_p]
                CFBundleCopyBundleURL.restype = c_void_p
                url = CFBundleCopyBundleURL(bundle)
                CFURLCopyFileSystemPath = Foundation.CFURLCopyFileSystemPath
                CFURLCopyFileSystemPath.argtypes = [c_void_p, c_int]
                CFURLCopyFileSystemPath.restype = c_void_p
                path = CFURLCopyFileSystemPath(url, c_int(0))
                CFStringGetCStringPtr = Foundation.CFStringGetCStringPtr
                CFStringGetCStringPtr.argtypes = [c_void_p, c_int]
                CFStringGetCStringPtr.restype = c_char_p
                self.app_path_mac = CFStringGetCStringPtr(path, 0)
                CFRelease = Foundation.CFRelease
                CFRelease.argtypes = [c_void_p]
                CFRelease(path)
                CFRelease(url)
            return self.app_path_mac.decode() + '/Contents/SharedSupport/bin/subl'
        if sublime.platform() == 'linux':
            return open('/proc/self/cmdline').read().split(chr(0))[0]
        return sys.executable
