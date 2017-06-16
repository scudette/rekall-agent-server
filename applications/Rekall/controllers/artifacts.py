# Artifact management.

# Forensic artifacts are a way of semantically specifying various parts of
# information to collect from a system. They encode domain specific information
# into an easily sharable specification.

# For more information, see https://github.com/ForensicArtifacts

def index():
    return dict()


TEMPLATE = """
# You can add comments anywhere in the artifact file.
name: ArtifactTemplate
doc: |
  Here you describe the artifact for humans.

sources:
  - type: REKALL_EFILTER
    attributes:

      # This is an EFilter query. Here "maps" is a plugin, and "proc_regex" is a
      # plugin arg.
      query: >
        select task.name, task.pid, start, end, flags, file_path
        from maps(proc_regex: "sshd") where flags.x and flags.w

      # If you want more control over output columns you can specify the
      # following list. If this is missing Rekall will deduce the columns
      # from the query but it will typically include more information.
      fields:
        - name: name
          type: unicode
        - name: pid
          type: int
        - name: start
          type: int
          style: address
        - name: end
          type: int
          style: address
        - name: flags
          type: unicode
        - name: file_path
          type: unicode

supported_os:
  # This can be one or more of Windows, Linux, Darwin, WindowsAPI,
  # LinuxAPI, DarwinAPI
  - Linux
"""


def add():
    return dict(artifact_text=TEMPLATE)
