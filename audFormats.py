from dataclasses import dataclass
import struct

@dataclass
class fmtchunks:
    chunk_name = 'fmt '
    chunkSize: int
    start_mark : int
    data : bytes
    audform : int
    numChan : int
    sampleRate : int    
    byteRate : int
    blockAlign : int
    bitsPerSample : int
    data_chunk_size : int

    def __init__(self, raw: bytes,start_mark = 0):
        self.start_mark = start_mark
        start_mark = start_mark + 4
        self.chunkSize = int.from_bytes(raw[start_mark :start_mark + 4], byteorder='little')
        start_mark = start_mark + 4
        if self.chunkSize == 16:
            self.audform = int.from_bytes(raw[start_mark :start_mark + 2], byteorder='little')
            start_mark = start_mark + 2
            self.numChan = int.from_bytes(raw[start_mark :start_mark + 2], byteorder='little')
            start_mark = start_mark + 2
            self.sampleRate = int.from_bytes(raw[start_mark :start_mark + 4], byteorder='little')
            start_mark = start_mark + 4
            self.byteRate = int.from_bytes(raw[start_mark :start_mark + 4], byteorder='little')
            start_mark = start_mark + 4
            self.blockAlign = int.from_bytes(raw[start_mark :start_mark + 2], byteorder='little')
            start_mark = start_mark + 2
            self.bitsPerSample = int.from_bytes(raw[start_mark :start_mark + 2], byteorder='little')
            start_mark = start_mark + 2
        else:
            raise Exception("fmt chunk size is not 16, this is not supported yet")
    def get_data(self, raw: bytes):
        data_start = self.start_mark + 24
        data_chunk_ID = raw[data_start : data_start + 4].decode('ascii') #+4
        if data_chunk_ID != 'data':
            return data_start
        self.data_chunk_size = int.from_bytes(raw[data_start + 4 : data_start + 8], byteorder='little') #4
        self.data = raw[data_start + 8 : data_start + 8 + self.data_chunk_size]
        end_mark = data_start + 8 + self.data_chunk_size
        
        return end_mark

@dataclass
class RIFF():
    child : list
    dataType : str
    container: str
    cont_size: int 
    chunk_name = 'RIFF'
    def __init__(self, raw: bytes, start_mark = 0):
        self.child = []
        self.container = raw[start_mark:start_mark + 4].decode('ascii') #AUDIO etc
        self.cont_size = int.from_bytes(raw[start_mark + 4:start_mark + 8], byteorder='little')
        
        self.start_mark = start_mark+8
        self.dataType = raw[self.start_mark:self.start_mark + 4].decode('ascii')
        self.start_mark = self.start_mark + 4
        childID = raw[self.start_mark:self.start_mark + 4].decode('ascii')
        self.setChild(raw, childID)
    def setChild(self, raw: bytes, childID: str):
        if childID == 'RIFF':
            self.child.append(RIFF(raw, self.start_mark))
        elif childID == 'fmt ': 
            self.child.append(fmtchunks(raw,self.start_mark))
            end_mark = self.child[-1].get_data(raw)
            if end_mark < self.start_mark + self.cont_size:
                chunkID = raw[end_mark : end_mark + 4].decode('ascii')
                self.setChild(raw, chunkID)
class WAVencoder():
    def __init__(self, riffobj=None,raw: bytes = None):
        if riffobj is None:
            if raw is None:
                raise Exception("Either riffobj or raw must be provided")
            self.riffobj = RIFF(raw)
        else:
            self.riffobj = riffobj
        
    def get_fmt_node_props(self,child):
        
        fmt_node = struct.pack("<4s I H H I I H H", child.chunk_name.encode('ascii'),
         child.chunkSize, 
         child.audform, 
         child.numChan,
          child.sampleRate, 
          child.byteRate, 
          child.blockAlign, 
          child.bitsPerSample)
        return fmt_node
    def make_child_structs(self,riffobj):
        riff_struct = struct.pack("<4s I 4s", riffobj.chunk_name.encode('ascii'), riffobj.cont_size, riffobj.dataType.encode('ascii'))
        for child in riffobj.child:
            if child.chunk_name == 'fmt ':
                fmt_packed = self.get_fmt_node_props(child)
                child_data_length =child.data_chunk_size
                data_packed = struct.pack("<4s I %ds" % child_data_length, 'data'.encode('ascii'), child_data_length, child.data)
                riff_struct += (fmt_packed + data_packed)
            else:
                riff_struct += self.make_child_structs(child)
        return riff_struct
            
                
       
class WAVdecoder():
    def __init__(self, raw: bytes):
        self.riff = RIFF(raw)
    def get_fmt_node_props(self,child):
        
        fmt_node = struct.pack("<4s I H H I I H H", child.chunk_name.encode('ascii'),
         child.chunkSize, 
         child.audform, 
         child.numChan,
          child.sampleRate, 
          child.byteRate, 
          child.blockAlign, 
          child.bitsPerSample)
        return fmt_node
    #def parse_data(self,child):


       

f = open('../testData/stereo','rb')
raw = f.read()
wav = WAVencoder(raw=raw)
with open("output.wav", "wb") as o:
    o.write(wav.make_child_structs(wav.riffobj))
    o.close()