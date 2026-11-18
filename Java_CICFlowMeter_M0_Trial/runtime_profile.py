"""Same pinned extractor for offline PCAP and live capture; no model changes."""
import json
import shutil
import threading
from extract_java_dataset import HERE, prepare, sha

LOCK = threading.Lock()


def resolve(model):
    if model == 'M0':
        return HERE / 'upstream', 'm0-current-unverified'
    if model != 'M1':
        raise ValueError('model must be M0 or M1')
    with LOCK:
        reference, manifest = prepare()
        wrapper = HERE / 'LiveTrial.java'
        runtime = HERE / 'output' / ('runtime_v2_' + manifest['commit'][:12] + '_' + sha(wrapper)[:12])
        marker = runtime / 'runtime.json'
        if not marker.exists():
            if runtime.exists():
                raise RuntimeError('Incomplete runtime: ' + str(runtime))
            shutil.copytree(reference, runtime, ignore=shutil.ignore_patterns('build', '.gradle', 'source.tar'))
            shutil.copy2(wrapper, runtime / 'src/main/java/cic/cs/unb/ca/ifm/LiveTrial.java')
            build = runtime / 'build.gradle'
            build.write_text(build.read_text().replace("args project.property('trialInput'), project.property('trialOutput')", "if (project.hasProperty('trialInput')) { args project.property('trialInput'), project.property('trialOutput') }"))
            with build.open('a') as stream:
                stream.write('''\ntask liveTrial(type: JavaExec) {
    main = "cic.cs.unb.ca.ifm.LiveTrial"
    classpath = sourceSets.main.runtimeClasspath
    jvmArgs '-Djava.library.path=jnetpcap/win/jnetpcap-1.4.r1500'
    args project.hasProperty('trialArgs') ? project.property('trialArgs').split('~') : ['--list']
}\n''')
            marker.write_text(json.dumps({'build': sha(runtime / 'build.gradle'), 'wrapper': sha(wrapper)}))
        saved = json.loads(marker.read_text())
        if sha(runtime / 'build.gradle') != saved['build']:
            raise RuntimeError('Runtime build modified')
        if sha(runtime / 'src/main/java/cic/cs/unb/ca/ifm/LiveTrial.java') != saved['wrapper']:
            raise RuntimeError('Runtime wrapper modified')
        for rel, digest in manifest['java_sha256'].items():
            if sha(runtime / rel) != digest:
                raise RuntimeError('Runtime extractor modified: ' + rel)
        for rel, key in [('jnetpcap/win/jnetpcap-1.4.r1425/jnetpcap.jar', 'native_jar_sha256'), ('jnetpcap/win/jnetpcap-1.4.r1500/jnetpcap.dll', 'native_dll_sha256')]:
            if sha(runtime / rel) != manifest[key]:
                raise RuntimeError('Runtime native library modified: ' + rel)
        return runtime, 'm1-improved-2022'
