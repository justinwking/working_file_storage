import os, urllib.parse, json, subprocess, shlex, argparse

Master_Dictionary ={'url':[],'commands':[]}

class ModelEntry:
    def __init__(self, folder, url, alt_name=False):
        self.folder = folder
        self.url = url
        self.workflow = "default"
        self.name = alt_name
        self.script_path = os.path.split(os.path.abspath(__file__))[0]
    def assign_workflow(self,new_workflow):
        self.workflow = new_workflow
    def to_dict(self):
        return {
            'folder': self.folder,
            'url': self.url,
            'workflow': self.workflow,
            'alt_name': self.name
        }  
    def append_to_master_dict(self, master_dict):
        folder = self.folder
        if folder not in master_dict:
            master_dict[folder] = []
        for entry in master_dict.get(folder, []):
            if entry.url == self.url:
                return  # URL already exists, skip adding this entry
        master_dict[folder].append(self.__dict__)
    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)
    def get_model(self):
        if not self.url:
            return 1
        self.filepath = os.path.join(self.script_path,"models",self.folder)
        os.makedirs(self.filepath, exist_ok=True)
        hf_token = os.environ.get('HF_TOKEN')
        civitai_token = os.environ.get('CIVITAI_TOKEN')
        
        auth_token = ""
        if self.url.startswith('https://huggingface.co') and hf_token:
            auth_token = hf_token
        elif self.url.startswith('https://civitai.com') and civitai_token:
            auth_token = civitai_token
        
        print(self.name)
        change_name = ""
        if self.name is not False:
            change_name=f"--output-document={os.path.join(self.filepath,self.name)}"  

        if auth_token:
            command = shlex.split(f'wget {change_name} --header="Authorization: Bearer {auth_token}" -qnc --content-disposition --show-progress -P "{self.filepath}" "{self.url}"')
        else:
            command = shlex.split(f'wget {change_name} -qnc --content-disposition --show-progress  -P " {self.filepath}" "{self.url}"')
        subprocess.run(command)

class NodeEntry:
    def __init__(self, git_link, command_list=[]):
        self.filepath = os.path.join(os.path.split(os.path.abspath(__file__))[0],"custom_nodes") # custom nodes folder
        parsed_url = urllib.parse.urlparse(git_link)
        self.folder = os.path.basename(parsed_url.path).replace(".git", "") # The name of the folder created.
        self.root = os.path.join(self.filepath,self.folder) # use this if creating a command from in the folder.
        self.url = git_link
        self.workflow = "default"
        self.commands = [["pip","install","-r",os.path.join(self.root,"requirements.txt")]]
        for i in command_list:
            self.commands.append(i)

    def assign_workflow(self,new_workflow):
        self.workflow = new_workflow

    def to_dict(self):
        return {
            'folder': self.folder,
            'url': self.url,
            'workflow': self.workflow,
            'commands': self.commands
        }

    def append_to_master_dict(self, master_dict):
        folder = self.folder
        if folder not in master_dict:
            master_dict[folder] = []
        for entry in master_dict.get(folder, []):
            if entry['url'] == self.url:
                return  # URL already exists, skip adding this entry
        master_dict[folder].append(self.__dict__)

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)
    def get_node(self):
        if not self.url:
            return 1
        os.makedirs(self.filepath, exist_ok=True)
        
        execute_commands = []
        execute_commands.append(shlex.split(f"git clone {self.url} {self.root}"))
        for com in self.commands:
            if isinstance(com,str):
                execute_commands.append(shlex.split(com))
            else:
                execute_commands.append(com)
        for exec_com in execute_commands:
            subprocess.run(exec_com)

class Workflow:
    def __init__(self, workflow_type):
        if not workflow_type:
            raise ValueError("Workflow type is required")
        self.type = workflow_type
        self.commands = []
        self.models = []
        self.nodes = []
    def command(self, command):
        self.commands.append(command)
    def model(self, model_entry):
        model_entry.assign_workflow(self.type)
        self.models.append(model_entry)
    def node(self, node_entry):
        node_entry.assign_workflow(self.type)
        self.nodes.append(node_entry)
    def populate_dictionary(self, master_dict=Master_Dictionary):
        for model in self.models:
            master_dict.setdefault("url",[])
            master_dict.setdefault(model.folder,[])
            if model.url not in master_dict["url"]:
                master_dict[model.folder].append(model)
                master_dict["url"].append(model.url)
            else:
                print(f'{model.url} is a duplicate' )
        for node in self.nodes:
            master_dict.setdefault("custom_nodes",[])
            if node.url not in master_dict['url']:
                master_dict["custom_nodes"].append(node)
                master_dict["url"].append(node.url)
            else:
                print(f'{node.url} is a duplicate' )
        for command in self.commands:
            master_dict.setdefault("commands",[])
            if command not in master_dict["commands"]:
                master_dict["commands"].append(command)
            else:
                print(f'{command} is a duplicate' )
    def print(self):
        print("Nodes:")
        for node in self.nodes:
            print(node)
        print("Models:")
        for  model in self.models:
            print(model)
        print("Commands:")
        for command in self.commands:
            print(command)

def provisioning_start(dict=Master_Dictionary):
    print("##############################################")
    print("#                                            #")
    print("#          Provisioning container            #")
    print("#                                            #")
    print("#         This will take some time           #")
    print("#                                            #")
    print("# Your container will be ready on completion #")
    print("#                                            #")
    print("##############################################")
    print("Starting provisioning...")

    for key, value in dict.items():
        print(key)
        if key == "url":
            pass
        elif key == "custom_nodes":
            for node in value:
                node.get_node()
        elif key == "commands":
            for command in value:
                if isinstance(command,str):
                    subprocess.run(shlex.split(command))
                else:
                    subprocess.run(command)
        else:
            for model in value:
                model.get_model()
        

    print("\nProvisioning complete:  Web UI will start now\n")

def create_workflow_dictionary():
    workflow_dictionary ={}

    default_workflow = Workflow("default")
    default_workflow.node(NodeEntry("https://github.com/ltdrdata/ComfyUI-Manager"))
    default_workflow.node(NodeEntry("https://github.com/cubiq/ComfyUI_essentials"))
    default_workflow.node(NodeEntry("https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite"))
    workflow_dictionary[default_workflow.type] = default_workflow

    animate_diff = Workflow("animate_diff")
    animate_diff.model(ModelEntry("animatediff_models","https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15.ckpt"))
    workflow_dictionary[animate_diff.type] = animate_diff
    
    animate_sdxl = Workflow("animate_sdxld")
    animate_sdxl.node(NodeEntry("https://github.com/Fannovel16/comfyui_controlnet_aux/"))
    animate_sdxl.node(NodeEntry("https://github.com/FizzleDorf/ComfyUI_FizzNodes"))
    animate_sdxl.node(NodeEntry("https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved"))
    animate_sdxl.node(NodeEntry("https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet"))
    animate_sdxl.model(ModelEntry("checkpoints","https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"))
    animate_sdxl.model(ModelEntry("checkpoints","https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors"))
    animate_sdxl.model(ModelEntry("vae","https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors"))
    animate_sdxl.model(ModelEntry("controlnet","https://huggingface.co/xinsir/controlnet-union-sdxl-1.0/resolve/main/diffusion_pytorch_model_promax.safetensors","controlnet-union-sdxl-1.0.safetensors"))
    workflow_dictionary[animate_sdxl.type] = animate_sdxl

    flux = Workflow("flux")
    flux.model(ModelEntry("controlnet","https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro/resolve/main/diffusion_pytorch_model.safetensors", "FLUX.1-dev-ControlNet-Union-Pro.safetensors"))
    workflow_dictionary[flux.type] = flux

    wan2=Workflow("wan2") # 2 text encoder, 1 image model, 1 text model, 1 vae
    wan2.command(["pip","install","-U","sageattention"])
    wan2.node(NodeEntry("https://github.com/kijai/ComfyUI-WanVideoWrapper.git"))
    wan2.node(NodeEntry("https://github.com/kijai/ComfyUI-KJNodes.git"))
    wan2.model(ModelEntry("text_encoders","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/open-clip-xlm-roberta-large-vit-huge-14_fp16.safetensors"))
    wan2.model(ModelEntry("text_encoders","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors"))
    wan2.model(ModelEntry("diffusion_models","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors"))
    wan2.model(ModelEntry("diffusion_models","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-T2V-1_3B_bf16.safetensors"))
    wan2.model(ModelEntry("vae","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors"))
    workflow_dictionary[wan2.type] = wan2

    wan2_large=Workflow("wan2_large") # 2 text encoder, 1 image model, 1 text model, 1 vae
    wan2_large.command(["pip","install","-U","sageattention"])
    wan2_large.node(NodeEntry("https://github.com/kijai/ComfyUI-WanVideoWrapper.git"))
    wan2_large.node(NodeEntry("https://github.com/kijai/ComfyUI-KJNodes.git"))
    wan2_large.model(ModelEntry("text_encoders","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/open-clip-xlm-roberta-large-vit-huge-14_visual_fp32.safetensors"))
    wan2_large.model(ModelEntry("text_encoders","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors"))
    wan2_large.model(ModelEntry("diffusion_models","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-720P_fp8_e4m3fn.safetensors"))
    wan2_large.model(ModelEntry("diffusion_models","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-T2V-14B_fp8_e4m3fn.safetensors"))
    wan2_large.model(ModelEntry("vae","https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_fp32.safetensors"))
    wan2_large.command(["pip","install","-U","sageattention"])
    workflow_dictionary[wan2_large.type] = wan2_large

    return workflow_dictionary

def create_help_file(dict):
    help_string = ""
    counter = 1
    for key, values in dict.items():
        help_string += (f"{counter}: {key}\n")
        counter +=1
    return help_string



if __name__ == "__main__":
    workflow_dict = create_workflow_dictionary()
    print(workflow_dict.keys())
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflows', nargs='+',default=['default'],help=create_help_file(workflow_dict))
    args = parser.parse_args()
    for i in args.workflows:
        if i in workflow_dict.keys():
            print(workflow_dict[str(i)]) 
            workflow_dict[str(i)].populate_dictionary()
    
    provisioning_start()
    
