from .base import Handler
from pyogp.lib.client.inventory import UDP_Inventory

class InventoryHandler(Handler):
    def onAgentConnected(self, agent):
        self.inventory = UDP_Inventory(agent)

    def onRegionConnect(self, region):
        res = region.message_handler.register("InventoryDescendents")
        res.subscribe(self.onInventoryDescendents)
        self.inventory.enable_callbacks()

    def onRegionConnected(self, region):
        client = self.manager.client

        # send inventory skeleton
        if hasattr(client, 'login_response') and 'inventory-skeleton' in client.login_response:
            self.out_queue.put(["InventorySkeleton",  client.login_response['inventory-skeleton']])

        self.inventory._parse_folders_from_login_response()


    def processFetchInventoryDescendents(self, *args):
        self.logger.debug('inventory processFetchInventoryDescendents')
        self.inventory.sendFetchInventoryDescendentsRequest(*args)


    def onInventoryDescendents(self, packet):
        logger = self.logger
        logger.debug('onInventoryDescendents')
        folder_id = packet['AgentData'][0]['FolderID']
        folders = [{'Name' : member.Name, 'ParentID' : str(member.ParentID), 'FolderID' : str(member.FolderID)} for member in self.inventory.folders if str(member.ParentID) == str(folder_id)]
        folder = [{'Name' : member.Name, 'ParentID' : str(member.ParentID), 'FolderID' : str(member.FolderID), 'Descendents' : packet['AgentData'][0]['Descendents']} for member in self.inventory.folders if str(member.FolderID) == str(folder_id)]
        folder = folder[0]
        folders.append(folder)
        # return # needs update on pyogp
        items =  [{'Name' : member.Name, 'FolderID' : str(member.FolderID), 'ItemID' : str(member.ItemID)} for member in self.inventory.items if str(member.FolderID) == str(folder_id)] 

        logger.debug("Packet", packet)
        logger.debug("Items", self.inventory.items, "Folders", self.inventory.folders)

        self.out_queue.put(['InventoryDescendents', str(folder_id), folders, items])


