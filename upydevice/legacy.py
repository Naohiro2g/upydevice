import ast
import subprocess
import shlex
import time
import serial
import serial.tools.list_ports  # BUG: This makes pyinstaller to fail
import struct
import multiprocessing
from array import array
from pexpect.replwrap import REPLWrapper


class W_UPYDEVICE:
    def __init__(self, ip_target, password, name=None, bundle_dir='', platform=None):
        self.password = password
        self.ip = ip_target
        self.response = None
        self.output = None
        self.bundle_dir = bundle_dir
        self.long_output = []
        self.process_raw = None
        self.name = name
        self.dev_class = 'WIRELESS'
        if name is None:
            self.name = 'wupydev_{}'.format(self.ip.split('.')[-1])
        self.output_queue = multiprocessing.Queue(maxsize=1)
        self._wconn = None
        self.repl_CONN = False
        self.platform = platform

    def _send_recv_cmd2(self, cmd):  # test method
        resp_recv = False
        command = shlex.split(cmd)
        while not resp_recv:
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE)
                resp_recv = True
            except Exception as e:
                pass

        stdout = process.communicate()
        try:
            resp = ast.literal_eval(
                stdout[0].decode('utf-8').split('\n')[6][4:-1])
        except Exception as e:
            try:
                resp = stdout[0].decode('utf-8').split('\n')[6][4:-1]
            except Exception as e:
                resp = None

            pass
        return resp, stdout

    def _cmd_r(self, cmd, pt=False):  # test method
        command = 'web_repl_cmd_r  -c "{}" -p {} -t {}'.format(
            cmd, self.password, self.ip)
        resp = self._send_recv_cmd2(command)
        if pt:
            print(resp[0])
        return resp[0]

    def _cmd(self, cmd):  # test method
        command = 'web_repl_cmd -c "{}" -p {} -t {}'.format(
            cmd, self.password, self.ip)
        resp = self._send_recv_cmd2(command)
        return resp[0]

    def _run_command_rl(self, command):  # test method
        end = False
        lines = []
        process = subprocess.Popen(
            shlex.split(command), stdout=subprocess.PIPE)
        while end is not True:
            if process.poll() is None:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip().decode()
                    lines.append(line)
                    if output.strip() == b'### closed ###':
                        end = True
            else:
                break
        rc = process.poll()
        return rc, lines

    def _cmd_rl(self, command, rt=False, evl=True):  # test method
        cmd = command
        cmd_str = 'web_repl_cmd_r -c "{}" -t {} -p {}'.format(
            cmd, self.ip, self.password)
        cmd_resp = self._run_command_rl(cmd_str)
        resp = cmd_resp[1]
        output = []
        for line in resp[6:]:
            if line == '### closed ###':
                pass
            else:
                try:
                    if line[0] == '>':
                        print(line[4:])
                        output.append(line[4:])
                    else:
                        print(line)
                        output.append(line)
                except Exception as e:
                    if len(line) == 0:
                        pass
                    else:
                        print(e)
                        pass
        if rt:
            if evl:
                return ast.literal_eval(output[0])
            else:
                return output

    def cmd(self, command, silent=False, p_queue=None, bundle_dir='', capture_output=False):  # best method
        cmd_str = self.bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format(
            command, self.ip, self.password)
        if bundle_dir is not '':
            cmd_str = bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format(
                command, self.ip, self.password)
        # print(group_cmd_str)
        self.long_output = []
        cmd = shlex.split(cmd_str)
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            for i in range(6):
                proc.stdout.readline()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if not silent:
                            print(resp[4:])
                        self.response = resp[4:]
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp[4:])
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp[4:])
                                except Exception as e:
                                    if 'bytearray' in resp[4:]:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp[4:]:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                    else:
                        if not silent:
                            print(resp)
                        self.response = resp
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp)
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp)
                                except Exception as e:
                                    if 'bytearray' in resp:

                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                else:
                    if not silent:
                        print(resp)

        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def cmd_p(self, command, silent=False, p_queue=None, bundle_dir='', capture_output=False):  # best method
        cmd_str = self.bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format(
            command, self.ip, self.password)
        if bundle_dir is not '':
            cmd_str = bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format(
                command, self.ip, self.password)
        # print(group_cmd_str)
        self.long_output = []
        cmd = shlex.split(cmd_str)
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            for i in range(6):
                proc.stdout.readline()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if not silent:
                            print('{}:{}'.format(self.name, resp[4:]))
                        self.response = resp[4:]
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp[4:])
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp[4:])
                                except Exception as e:
                                    if 'bytearray' in resp[4:]:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp[4:]:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                    else:
                        if not silent:
                            print('{}:{}'.format(self.name, resp))
                        self.response = resp
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp)
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp)
                                except Exception as e:
                                    if 'bytearray' in resp:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                else:
                    if not silent:
                        print('{}:{}'.format(self.name, resp))
        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def _cmd_nb(self, command, silent=False, time_out=2, bundle_dir=''):  # non blocking device method
        cmd_str = self.bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format(
            command, self.ip, self.password)
        if bundle_dir is not '':
            cmd_str = bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format(
                command, self.ip, self.password)
        # print(group_cmd_str)
        self.long_output = []
        cmd = shlex.split(cmd_str)
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            for i in range(6):
                proc.stdout.readline()
            time.sleep(time_out)
            proc.terminate()

        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def cmd_nb(self, command, silent=False, time_out=2, block_dev=True):
        if not block_dev:
            self.dev_process_raw = multiprocessing.Process(
                target=self._cmd_nb, args=(command, silent, time_out, self.bundle_dir))
            self.dev_process_raw.start()
        else:
            self.dev_process_raw = multiprocessing.Process(
                target=self.cmd, args=(command, silent, self.output_queue, self.bundle_dir))
            self.dev_process_raw.start()

    def get_opt(self):
        try:
            self.output = self.output_queue.get(block=False)
        except Exception:
            pass

    def reset(self, bundle_dir='', output=True):
        reset_cmd_str = self.bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format('D',
                                                                                    self.ip, self.password)
        if bundle_dir is not '':
            reset_cmd_str = bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format('D',
                                                                                   self.ip, self.password)
        reset_cmd = shlex.split(reset_cmd_str)
        if output:
            print('Rebooting device...')
        try:
            proc = subprocess.Popen(
                reset_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            for i in range(6):
                proc.stdout.readline()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if output:
                            print(resp[4:])
                    else:
                        if output:
                            print(resp)
                else:
                    if output:
                        print(resp)
            if output:
                print('Done!')
        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def get_output(self):
        try:
            self.output = ast.literal_eval(self.response)
        except Exception as e:
            if 'bytearray' in self.response:
                try:
                    self.output = bytearray(ast.literal_eval(
                        self.response.strip().split('bytearray')[1]))
                except Exception as e:
                    pass
            else:
                if 'array' in self.response:
                    try:
                        arr = ast.literal_eval(
                            self.response.strip().split('array')[1])
                        self.output = array(arr[0], arr[1])
                    except Exception as e:
                        pass
            pass

    def kbi(self, bundle_dir='', output=True, traceback=False, filter_ban=True):
        reset_cmd_str = self.bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format('\x03',
                                                                                    self.ip, self.password)
        if bundle_dir is not '':
            reset_cmd_str = bundle_dir+'web_repl_cmd_r -c "{}" -t {} -p {}'.format(hex(3),
                                                                                   self.ip, self.password)
        reset_cmd = shlex.split(reset_cmd_str)
        if output:
            print('KeyboardInterrupt sent!')
        kw_ban = ["MicroPython", "module with", 'Type "help()" for more information.']
        try:
            proc = subprocess.Popen(
                reset_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            for i in range(2):
                proc.stdout.readline()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if traceback:
                            if filter_ban:
                                if not any([kw in resp[4:] for kw in kw_ban]):
                                    print(resp[4:])
                            else:
                                print(resp[4:])
                    else:
                        if traceback:
                            if filter_ban:
                                if not any([kw in resp for kw in kw_ban]):
                                    if resp != '':
                                        print(resp)
                            else:
                                print(resp)
                else:
                    if traceback:
                        if filter_ban:
                            if resp != '':
                                print(resp)
                        else:
                            print(resp)
                if 'KeyboardInterrupt' in resp:
                    while proc.poll() is None:
                        proc.stdout.readline()
                    break
            if output:
                print('Done!')
        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def is_reachable(self, n_tries=2, max_loss=1, debug=False, timeout=2):
        ping_cmd_str = 'ping -c {} {} -t {}'.format(n_tries, self.ip, timeout)
        ping_cmd = shlex.split(ping_cmd_str)
        timeouts = 0
        down_kw = ['Unreachable', 'down', 'timeout']
        try:
            proc = subprocess.Popen(
                ping_cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if debug:
                    print(resp)
                if any([kw in resp for kw in down_kw]):
                    timeouts += 1

            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                if debug:
                    print(message[:-1].decode())

        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                if debug:
                    print(message[:-1].decode())

        if timeouts >= max_loss:
            if debug:
                print('DEVICE IS DOWN OR SIGNAL RSSI IS TO LOW')
            return False
        else:
            return True

    def open_wconn(self, bundle_dir='', dbg=False):
        self._wconn = REPLWrapper(
            bundle_dir+'web_repl_conn {} -p {}'.format(self.ip, self.password), ">>> ", None)
        self.repl_CONN = True
        if dbg:
            print('WebREPL connection ready!')

    def wr_cmd(self, cmd_msg, dbg=False, silent=False, rtn=True, timeout=1, follow=True, pipe=None, m_kbi=False):
        cmd = self._wconn.child.sendline(cmd_msg)
        s_output = False
        try:
            raw_out = ' '
            cmd_echo = self._wconn.child.readline()
            timed_out = False
            len_output_now = 0
            len_output_prev = 0
            expect_prompt = ' '
            time.sleep(0.2)
            while not self._wconn.prompt.strip() in expect_prompt.strip():
                try:
                    raw_out += self._wconn.child.read_nonblocking(
                        2**16, timeout)
                    s_output = True
                    expect_prompt = raw_out.split('\n')[-1]
                    if follow:
                        outlines = [line for line in raw_out.split(
                            '...')[-1].splitlines()[:-1] if line != '']  # line.strip()
                        len_output_now = len(outlines)
                        if dbg:
                            print(outlines)
                            print('LEN NOW: {}'.format(len_output_now))
                            print('LEN PREV: {}'.format(len_output_prev))
                        if len_output_now > len_output_prev:
                            diff_len = len_output_now - len_output_prev
                            len_output_prev = len(outlines)
                            for line in outlines[-diff_len:]:
                                if line == outlines[0]:
                                    line = line[1:]
                                cmds = [val for val in cmd_msg.split(
                                    '\r') if val != '']
                                if line.replace('>>> ', '') != cmd_msg and line.replace('>>> ', '').strip() not in cmds and '\x08' not in line.replace('>>> ', ''):
                                    self.response = line.replace('>>> ', '')
                                    if pipe is not None:
                                        pipe(self.response+'\n')
                                    else:
                                        if not silent:
                                            print(self.response)
                        elif len_output_now < len_output_prev:
                            len_output_prev = 0

                except KeyboardInterrupt:
                    # print('KBI!')
                    # self._wconn.child.sendline('C' + '\r')
                    self.close_wconn()
                    self.kbi(traceback=True, output=False)
                    if self.platform == 'esp8266':
                        self.cmd('\x0d', silent=True)
                    time.sleep(0.2)
                    self.open_wconn()
                    flush = self._wconn.child.read_nonblocking(256, 0.1)
                    s_output = False
                    break

                except Exception as e:
                    if dbg:
                        print(e)
                        print(expect_prompt)
                    timed_out = True
                # except KeyboardInterrupt:
                #     if m_kbi:
                #         self.close_wconn()
                #         self.kbi()
                #         time.sleep(0.5)
                #         self.open_wconn()
                # except EOFError:
                #     if m_kbi:
                #         self.close_wconn()
                #         self.kbi()
                #         time.sleep(0.5)
                #         self.open_wconn()
        except Exception as e:
            if dbg:
                print('Timeout')
        if s_output:
            s_output = raw_out.replace('>>>', '').strip().split('\n')[-1]
            self.process_raw = raw_out
            outlines = [line.strip() for line in self.process_raw.split(
                '...')[-1].splitlines()[:-1] if line != '']
            for line in outlines:
                if line != cmd_msg:
                    self.response = line
                    if rtn:
                        self.get_output()
                    if not silent:
                        if not follow:
                            print(line)

    def close_wconn(self):
        self._wconn.child.close()
        self.repl_CONN = False


# S_UPYDEVICE

class S_UPYDEVICE:
    def __init__(self, serial_port, timeout=100, baudrate=9600, name=None, bundle_dir='', reset=True):
        self.serial_port = serial_port
        self.returncode = None
        self.timeout = timeout
        self.baudrate = baudrate
        self.name = name
        self.process_raw = None
        self.dev_class = 'SERIAL'
        self.bundle_dir = bundle_dir
        if name is None:
            self.name = 'supydev_{}'.format(self.serial_port.split('/')[-1])
        self.output_queue = multiprocessing.Queue(maxsize=1)
        self.picocom_cmd = shlex.split(
            'picocom -port {} -qcx {} -b{}'.format(self.serial_port, self.timeout, self.baudrate))
        self.response = None
        self.response_object = None
        self.output = None
        self.long_output = []
        self._wconn = None
        self.repl_CONN = False
        self.serial = serial.Serial(self.serial_port, self.baudrate)
        if reset:
            self.reset(output=False)
            # self._reset()
            self.serial.close()

    def get_output(self):
        try:
            self.output = ast.literal_eval(self.response)
        except Exception as e:
            if 'bytearray' in self.response:
                try:
                    self.output = bytearray(ast.literal_eval(
                        self.response.strip().split('bytearray')[1]))
                except Exception as e:
                    pass
            else:
                if 'array' in self.response:
                    try:
                        arr = ast.literal_eval(
                            self.response.strip().split('array')[1])
                        self.output = array(arr[0], arr[1])
                    except Exception as e:
                        pass
            pass

    def enter_cmd(self):
        if not self.serial.is_open:
            self.serial.open()
        self.serial.write(struct.pack('i', 0x0d))  # CR
        self.serial.close()

    def cmd(self, command, silent=False, p_queue=None, bundle_dir='', capture_output=False, timeout=None):
        self.long_output = []
        self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
            shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
        if timeout is not None:
            self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), timeout, self.baudrate, self.serial_port))
        if bundle_dir is not '':
            self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
            if timeout is not None:
                self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                    shlex.quote(command), timeout, self.baudrate, self.serial_port))
        try:
            proc = subprocess.Popen(
                self.picocom_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            time.sleep(0.2)
            for i in range(2):
                self.enter_cmd()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if not silent:
                            print(resp[4:])
                        self.response = resp[4:]
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp[4:])
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp[4:])
                                except Exception as e:
                                    if 'bytearray' in resp[4:]:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp[4:]:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                    else:
                        if resp != '{}\r'.format(command):
                            if not silent:
                                print(resp)
                        self.response = resp
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp)
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp)
                                except Exception as e:
                                    if 'bytearray' in resp:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                else:
                    if not silent:
                        print(resp)

        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def cmd_p(self, command, silent=False, p_queue=None, bundle_dir='', capture_output=False, timeout=None):
        self.long_output = []
        self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
            shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
        if timeout is not None:
            self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), timeout, self.baudrate, self.serial_port))
        if bundle_dir is not '':
            self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
            if timeout is not None:
                self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                    shlex.quote(command), timeout, self.baudrate, self.serial_port))
        try:
            proc = subprocess.Popen(
                self.picocom_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            time.sleep(0.2)
            for i in range(2):
                self.enter_cmd()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if not silent:
                            print('{}:{}'.format(self.name, resp[4:]))
                        self.response = resp[4:]
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp[4:])
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp[4:])
                                except Exception as e:
                                    if 'bytearray' in resp[4:]:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp[4:]:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                    else:
                        if resp != '{}\r'.format(command):
                            if not silent:
                                print('{}:{}'.format(self.name, resp))
                        self.response = resp
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp)
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp)
                                except Exception as e:
                                    if 'bytearray' in resp:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                else:
                    if not silent:
                        print('{}:{}'.format(self.name, resp))

        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def cmd_nb(self, command, silent=False):
        self.dev_process_raw = multiprocessing.Process(
            target=self.cmd, args=(command, silent, self.output_queue, self.bundle_dir))
        self.dev_process_raw.start()

    def get_opt(self):
        try:
            self.output = self.output_queue.get(block=False)
        except Exception:
            pass

    def reset(self, output=True):
        if output:
            print('Rebooting upydevice...')
        if not self.serial.is_open:
            self.serial.open()
        # time.sleep(1)
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        # time.sleep(1)
        self.serial.write(struct.pack('i', 0x0d))
        self.serial.write(struct.pack('i', 0x04))  # EOT
        self.serial.write(struct.pack('i', 0x0d))  # CR
        self.serial.flush()
        # print(self.serial.inWaiting())
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        self.serial.write(struct.pack('i', 0x0d))
        # time.sleep(1)
        self.serial.close()
        if output:
            print('Done!')

    def kbi(self, output=True):
        if output:
            print('KeyboardInterrupt sent!')
        if not self.serial.is_open:
            self.serial.open()
        # time.sleep(1)
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        # time.sleep(1)
        self.serial.write(struct.pack('i', 0x0d))
        self.serial.write(struct.pack('i', 0x03))  # EOT
        self.serial.write(struct.pack('i', 0x0d))  # CR
        self.serial.flush()
        # print(self.serial.inWaiting())
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        self.serial.write(struct.pack('i', 0x0d))
        # time.sleep(1)
        self.serial.close()
        if output:
            print('Done!')

    def open_wconn(self, bundle_dir='', dbg=False):
        self._wconn = REPLWrapper(
            bundle_dir + "picocom -t '>>> ' -b{} {}".format(self.baudrate, self.serial_port), ">>> ", None)
        cmd = self._wconn.child.sendline("\x08"*len('>>> ')+"\r")
        self.repl_CONN = True
        if dbg:
            print('Serial connection ready!')

    def wr_cmd(self, cmd_msg, dbg=False, silent=False, rtn=True, timeout=1, follow=True, pipe=None):
        if cmd_msg.endswith('\r'):
            cmd = self._wconn.child.sendline(cmd_msg)
        else:
            cmd = self._wconn.child.sendline(cmd_msg + '\r')
        s_output = False
        try:
            raw_out = ' '
            cmd_echo = self._wconn.child.readline()
            timed_out = False
            len_output_now = 0
            len_output_prev = 0
            expect_prompt = ' '
            # time.sleep(0.2)
            while not self._wconn.prompt.strip() in expect_prompt.strip():
                try:
                    raw_out += self._wconn.child.read_nonblocking(
                        2**16, timeout)
                    s_output = True
                    expect_prompt = raw_out.split('\n')[-1]
                    if follow:
                        outlines = [line for line in raw_out.split(
                            '...')[-1].splitlines()[:-1] if line != '']  # line.strip()
                        len_output_now = len(outlines)
                        if dbg:
                            print(outlines)
                            print('LEN NOW: {}'.format(len_output_now))
                            print('LEN PREV: {}'.format(len_output_prev))
                        if len_output_now > len_output_prev:
                            diff_len = len_output_now - len_output_prev
                            len_output_prev = len(outlines)
                            for line in outlines[-diff_len:]:
                                if line == outlines[0]:
                                    line = line[1:]
                                cmds = [val for val in cmd_msg.split(
                                    '\r') if val != '']
                                if line.replace('>>> ', '') != cmd_msg and line.replace('>>> ', '').strip() not in cmds and '\x08' not in line.replace('>>> ', ''):
                                    self.response = line.replace('>>> ', '')
                                    if pipe is not None:
                                        pipe(self.response+'\n')
                                    else:
                                        if not silent:
                                            print(self.response)
                        elif len_output_now < len_output_prev:
                            len_output_prev = 0

                except KeyboardInterrupt:
                    print('^C')
                    self._wconn.child.sendline('\x03' + '\r')
                except Exception as e:
                    if dbg:
                        print(e)
                        print(expect_prompt)
                    timed_out = True
        except Exception as e:
            if dbg:
                print('Timeout')
        if s_output:
            s_output = raw_out.replace('>>>', '').strip().split('\n')[-1]
            self.process_raw = raw_out
            outlines = [line.strip() for line in self.process_raw.split(
                '...')[-1].splitlines()[:-1] if line != '']
            for line in outlines:
                if line != cmd_msg:
                    self.response = line
                    if rtn:
                        self.get_output()
                    if not silent:
                        if not follow:
                            print(line)

    def close_wconn(self):
        self._wconn.child.close()
        self.repl_CONN = False


# PYBOARD


class PYBOARD:
    def __init__(self, serial_port, timeout=100, baudrate=9600, name=None, bundle_dir=''):
        self.serial_port = serial_port
        self.returncode = None
        self.timeout = timeout
        self.baudrate = baudrate
        self.picocom_cmd = None
        self.response = None
        self.response_object = None
        self.name = name
        self.dev_class = 'SERIAL'
        self.bundle_dir = bundle_dir
        if name is None:
            self.name = 'pyboard_{}'.format(self.serial_port.split('/')[-1])
        self.output_queue = multiprocessing.Queue(maxsize=1)
        self.output = None
        self.process_raw = None
        self.long_output = []
        self._wconn = None
        self.repl_CONN = False
        self.serial = serial.Serial(self.serial_port, self.baudrate)
        self.reset(output=False)
        self.reset(output=False)
        # self.serial.close()
        for i in range(3):
            self.enter_cmd()

    def get_output(self):
        try:
            self.output = ast.literal_eval(self.response)
        except Exception as e:
            if 'bytearray' in self.response:
                try:
                    self.output = bytearray(ast.literal_eval(
                        self.response.strip().split('bytearray')[1]))
                except Exception as e:
                    pass
            else:
                if 'array' in self.response:
                    try:
                        arr = ast.literal_eval(
                            self.response.strip().split('array')[1])
                        self.output = array(arr[0], arr[1])
                    except Exception as e:
                        pass
            pass

    def enter_cmd(self):
        if not self.serial.is_open:
            self.serial.open()
        self.serial.write(struct.pack('i', 0x0d))  # CR
        # self.serial.close()

    def cmd(self, command, silent=False, p_queue=None, bundle_dir='', out_print=True, capture_output=False, timeout=None):
        out_print = not silent
        self.long_output = []
        self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
            shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
        if timeout is not None:
            self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), timeout, self.baudrate, self.serial_port))
        if bundle_dir is not '':
            self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
            if timeout is not None:
                self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                    shlex.quote(command), timeout, self.baudrate, self.serial_port))
        try:
            proc = subprocess.Popen(
                self.picocom_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            time.sleep(0.05)  # KEY FINE TUNNING
            for i in range(2):
                self.enter_cmd()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if out_print:
                            print(resp[4:])
                        self.response = resp[4:]
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp[4:])
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp[4:])
                                except Exception as e:
                                    if 'bytearray' in resp[4:]:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp[4:]:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                    else:
                        if resp != '{}\r'.format(command):
                            if out_print:
                                print(resp)
                        self.response = resp
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp)
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp)
                                except Exception as e:
                                    if 'bytearray' in resp:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                else:
                    print(resp)

            while self.serial.inWaiting() > 0:
                self.serial.read()

        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def cmd_p(self, command, silent=False, p_queue=None, bundle_dir='', out_print=True, capture_output=False, timeout=None):
        out_print = not silent
        self.long_output = []
        self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
            shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
        if timeout is not None:
            self.picocom_cmd = shlex.split(self.bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), timeout, self.baudrate, self.serial_port))
        if bundle_dir is not '':
            self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                shlex.quote(command), self.timeout, self.baudrate, self.serial_port))
            if timeout is not None:
                self.picocom_cmd = shlex.split(bundle_dir+'picocom -t {} -qx {} -b{} {}'.format(
                    shlex.quote(command), timeout, self.baudrate, self.serial_port))
        try:
            proc = subprocess.Popen(
                self.picocom_cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            time.sleep(0.05)  # KEY FINE TUNNING
            for i in range(2):
                self.enter_cmd()
            while proc.poll() is None:
                resp = proc.stdout.readline()[:-1].decode()
                if len(resp) > 0:
                    if resp[0] == '>':
                        if out_print:
                            print('{}:{}'.format(self.name, resp[4:]))
                        self.response = resp[4:]
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp[4:])
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp[4:])
                                except Exception as e:
                                    if 'bytearray' in resp[4:]:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp[4:]:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                    else:
                        if resp != '{}\r'.format(command):
                            if out_print:
                                print('{}:{}'.format(self.name, resp))
                        self.response = resp
                        self.get_output()
                        if capture_output:
                            self.long_output.append(resp)
                        if p_queue is not None:
                            try:
                                try:
                                    output = ast.literal_eval(resp)
                                except Exception as e:
                                    if 'bytearray' in resp:
                                        output = bytearray(ast.literal_eval(
                                            resp.strip().split('bytearray')[1]))
                                    else:
                                        if 'array' in resp:
                                            arr = ast.literal_eval(
                                                resp.strip().split('array')[1])
                                            output = array(arr[0], arr[1])
                                    pass
                                p_queue.put((
                                    output), block=False)
                            except Exception as e:
                                pass
                else:
                    print('{}:{}'.format(self.name, resp))

            while self.serial.inWaiting() > 0:
                self.serial.read()

        except KeyboardInterrupt:
            time.sleep(1)
            result = proc.stdout.readlines()
            for message in result:
                print(message[:-1].decode())

    def cmd_nb(self, command, silent=False):
        self.dev_process_raw = multiprocessing.Process(
            target=self.cmd, args=(command, silent, self.output_queue, self.bundle_dir))
        self.dev_process_raw.start()

    def get_opt(self):
        try:
            self.output = self.output_queue.get(block=False)
        except Exception:
            pass

    def reset(self, output=True):
        if output:
            print('Rebooting pyboard...')
        if not self.serial.is_open:
            self.serial.open()
        # time.sleep(1)
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        # time.sleep(1)
        self.serial.write(struct.pack('i', 0x0d))
        self.serial.write(struct.pack('i', 0x04))  # EOT
        self.serial.write(struct.pack('i', 0x0d))  # CR
        self.serial.flush()
        # print(self.serial.inWaiting())
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        self.serial.write(struct.pack('i', 0x0d))
        # time.sleep(1)
        # self.serial.close()
        if output:
            print('Done!')

    def kbi(self, output=True):
        if output:
            print('KeyboardInterrupt sent!')
        if not self.serial.is_open:
            self.serial.open()
        # time.sleep(1)
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        # time.sleep(1)
        self.serial.write(struct.pack('i', 0x0d))
        self.serial.write(struct.pack('i', 0x03))  # ETX
        self.serial.write(struct.pack('i', 0x0d))  # CR
        self.serial.flush()
        # print(self.serial.inWaiting())
        while self.serial.inWaiting() > 0:
            self.serial.read()
        # print(self.serial.inWaiting())
        self.serial.write(struct.pack('i', 0x0d))
        # time.sleep(1)
        # self.serial.close()
        if output:
            print('Done!')

    def open_wconn(self, bundle_dir='', dbg=False):
        self._wconn = REPLWrapper(
            bundle_dir + "picocom -t '>>> ' -b{} {}".format(self.baudrate, self.serial_port), ">>> ", None)
        cmd = self._wconn.child.sendline("\x08"*len('>>> ')+"\r")
        self.repl_CONN = True
        if dbg:
            print('Serial connection ready!')

    def wr_cmd(self, cmd_msg, dbg=False, silent=False, rtn=True, timeout=1, follow=True, pipe=None):
        if cmd_msg.endswith('\r'):
            cmd = self._wconn.child.sendline(cmd_msg)
        else:
            cmd = self._wconn.child.sendline(cmd_msg + '\r')
        s_output = False
        try:
            raw_out = ' '
            cmd_echo = self._wconn.child.readline()
            timed_out = False
            len_output_now = 0
            len_output_prev = 0
            expect_prompt = ' '
            # time.sleep(0.2)
            while not self._wconn.prompt.strip() in expect_prompt.strip():
                try:
                    raw_out += self._wconn.child.read_nonblocking(
                        2**16, timeout)
                    s_output = True
                    expect_prompt = raw_out.split('\n')[-1]
                    if follow:
                        outlines = [line for line in raw_out.split(
                            '...')[-1].splitlines()[:-1] if line != '']  # line.strip()
                        len_output_now = len(outlines)
                        if dbg:
                            print(outlines)
                            print('LEN NOW: {}'.format(len_output_now))
                            print('LEN PREV: {}'.format(len_output_prev))
                        if len_output_now > len_output_prev:
                            diff_len = len_output_now - len_output_prev
                            len_output_prev = len(outlines)
                            for line in outlines[-diff_len:]:
                                if line == outlines[0]:
                                    line = line[1:]
                                cmds = [val for val in cmd_msg.split(
                                    '\r') if val != '']
                                if line.replace('>>> ', '') != cmd_msg and line.replace('>>> ', '').strip() not in cmds and '\x08' not in line.replace('>>> ', ''):
                                    self.response = line.replace('>>> ', '')
                                    if pipe is not None:
                                        pipe(self.response+'\n')
                                    else:
                                        if not silent:
                                            print(self.response)
                        elif len_output_now < len_output_prev:
                            len_output_prev = 0

                except KeyboardInterrupt:
                    print('^C')
                    self._wconn.child.sendline('\x03' + '\r')
                except Exception as e:
                    if dbg:
                        print(e)
                        print(expect_prompt)
                    timed_out = True

        except Exception as e:
            if dbg:
                print('Timeout')
        if s_output:
            s_output = raw_out.replace('>>>', '').strip().split('\n')[-1]
            self.process_raw = raw_out
            outlines = [line.strip() for line in self.process_raw.split(
                '...')[-1].splitlines()[:-1] if line != '']
            for line in outlines:
                if line != cmd_msg:
                    self.response = line
                    if rtn:
                        self.get_output()
                    if not silent:
                        if not follow:
                            print(line)

    def close_wconn(self):
        self._wconn.child.close()
        self.repl_CONN = False


class GROUP:
    def __init__(self, devs=[None], name=None):
        self.name = name
        self.devs = {dev.name: dev for dev in devs}
        self.dev_process_raw_dict = None
        self.output = None
        self.output_queue = {
            dev.name: multiprocessing.Queue(maxsize=1) for dev in devs}

    def cmd(self, command, group_silent=False, dev_silent=False, ignore=[], include=[]):
        if len(include) == 0:
            include = [dev for dev in self.devs.keys()]
        for dev in ignore:
            include.remove(dev)
        for dev in include:
            if not group_silent:
                print('Sending command to {}'.format(dev))
            self.devs[dev].cmd(command, silent=dev_silent)
        self.output = {dev: self.devs[dev].output for dev in include}

    def cmd_p(self, command, group_silent=False, dev_silent=False, ignore=[], include=[], blocking=True, id=False):
        if not id:
            self.dev_process_raw_dict = {dev: multiprocessing.Process(target=self.devs[dev].cmd, args=(
                command, dev_silent, self.output_queue[dev])) for dev in self.devs.keys()}
            if len(include) == 0:
                include = [dev for dev in self.devs.keys()]
            for dev in ignore:
                include.remove(dev)
            if not group_silent:
                print('Sending command to: {}'.format(', '.join(include)))
            for dev in include:
                # self.devs[dev].cmd(command, silent=dev_silent)
                self.dev_process_raw_dict[dev].start()

            while blocking:
                dev_proc_state = [self.dev_process_raw_dict[dev].is_alive(
                ) for dev in self.dev_process_raw_dict.keys()]
                if all(state is False for state in dev_proc_state):
                    time.sleep(0.1)
                    if not group_silent:
                        print('Done!')
                    break

            try:
                self.output = {dev: self.output_queue[dev].get(
                    timeout=2) for dev in include}
            except Exception as e:
                pass
            for dev in include:
                try:
                    self.devs[dev].output = self.output[dev]
                except Exception as e:
                    pass
        else:
            self.dev_process_raw_dict = {dev: multiprocessing.Process(target=self.devs[dev].cmd_p, args=(
                command, dev_silent, self.output_queue[dev])) for dev in self.devs.keys()}
            if len(include) == 0:
                include = [dev for dev in self.devs.keys()]
            for dev in ignore:
                include.remove(dev)
            if not group_silent:
                print('Sending command to: {}'.format(', '.join(include)))
            for dev in include:
                # self.devs[dev].cmd(command, silent=dev_silent)
                self.dev_process_raw_dict[dev].start()

            while blocking:
                dev_proc_state = [self.dev_process_raw_dict[dev].is_alive(
                ) for dev in self.dev_process_raw_dict.keys()]
                if all(state is False for state in dev_proc_state):
                    time.sleep(0.1)
                    if not group_silent:
                        print('Done!')
                    break

            try:
                self.output = {dev: self.output_queue[dev].get(
                    timeout=2) for dev in include}
            except Exception as e:
                pass
            for dev in include:
                try:
                    self.devs[dev].output = self.output[dev]
                except Exception as e:
                    pass

    def get_opt(self):
        try:
            self.output = {dev: self.output_queue[dev].get(
                timeout=2) for dev in self.devs.keys()}
        except Exception as e:
            pass
        for dev in self.devs.keys():
            try:
                self.devs[dev].output = self.output[dev]
            except Exception as e:
                pass

    def reset(self, group_silent=False, output_dev=True, ignore=[], include=[]):
        if len(include) == 0:
            include = [dev for dev in self.devs.keys()]
        for dev in ignore:
            include.remove(dev)
        for dev in include:
            if not group_silent:
                print('Rebooting {}'.format(dev))
            self.devs[dev].reset(output=output_dev)