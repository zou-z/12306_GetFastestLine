import requests
import re
import time

outcome={
	'Common':(
		'完成',
		'失败',
		'按回车键退出'),
	'GetStationVersion':(
		'正在获取最新的车站代号版本...',
		'获取最新的车站代号版本出错!',
		'最新的车站代号版本:'),
	'GetStationName':(
		'正在获取所有车站的代号...',
		'完成'),
	'GetLines':(
		'正在获取各路程信息(按十天后的时间:{0})...',
		'->获取 {0} 到 {1} 的车票信息...',
		'输入的车站名称有误!'),
	'GetValidLine':(
		'正在计算所有可行的路线...',),
	'CalcFullTime':(
		'正在计算各路线耗时...',),
	'SortLines':(
		'按时间升序显示结果:',
		'(共{0}条记录)')
}

class Ticket(object):
	def __init__(self):
		self.url='https://kyfw.12306.cn/otn/leftTicket/queryX?'
		self.session=requests.session()
		self.headers={ 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36' }
		self.version=''
		self.stations=''
		self.map={}

	def GetStationVersion(self):
		url='https://kyfw.12306.cn/otn/leftTicket/init?linktypeid=dc'
		result=self.session.get(url=url,headers=self.headers).content.decode('utf-8')
		version=re.findall('station_version=(.*?)"',result)
		if not version:
			return False
		self.version=version[0]

	def GetStationName(self):
		url='https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version='+self.version
		result=self.session.get(url=url,headers=self.headers).content.decode('utf-8')
		self.stations=result

	def GetCityCode(self,city):
		code=re.findall('{0}\|(.*?)\|'.format(city),self.stations,re.S)
		if 1!=len(code):
			return False
		return code[0]

	def GetAllTrain(self,date='2019-03-01',from_s='NCG',to_s='ZZF',t_type='ADULT'):
		para=['leftTicketDTO.train_date=','&leftTicketDTO.from_station=','&leftTicketDTO.to_station=','&purpose_codes=']
		full_url=self.url+para[0]+date+para[1]+from_s+para[2]+to_s+para[3]+t_type;
		response=self.session.get(url=full_url,headers=self.headers).json()
		self.map.update(response['data']['map'])
		return self.__ParseResponse(response['data']['result'])

	def __ParseResponse(self,response):
		trains=[]
		for item in response:
			tmp=item.split('|')
			trainMsg={
				'name':tmp[3],
				'from':tmp[6],
				'to':tmp[7],
				'time_start':tmp[8],
				'time_end':tmp[9],
				'time_spend':tmp[10]
			}
			trains.append(trainMsg)
		return trains

	def GetCityName(self,city_code):
		for i in self.map:
			if i==city_code:
				return self.map[i]
		return city_code

class GetFastestLine(object):
	def __init__(self,citys,time_area=12,date=time.strftime("%Y-%m-%d",time.localtime(time.time()+864000))):
		self.citys=citys.split()
		self.time_area=time_area
		self.date=date
		self.ticket=Ticket()
		self.lines=[]
		self.lines_sorted=[]

	def Start(self):
		print(outcome['GetStationVersion'][0])
		if False==self.ticket.GetStationVersion():
			print(outcome['Common'][1]+','+outcome['GetStationVersion'][1])
			exit(0)
		print(outcome['Common'][0]+','+outcome['GetStationVersion'][2],self.ticket.version)
		
		print(outcome['GetStationName'][0])
		self.ticket.GetStationName()
		print(outcome['Common'][0])
		
		print(outcome['GetLines'][0].format(self.date))
		for i in range(len(self.citys)-1):
			print(outcome['GetLines'][1].format(self.citys[i],self.citys[i+1]))
			if False==self.__GetLines(self.citys[i],self.citys[i+1]):
				print(outcome['Common'][1]+','+outcome['GetLines'][2])
				exit(0)
		print(outcome['Common'][0])
		
		print(outcome['GetValidLine'][0])
		for i in self.lines[0]:
			self.__GetValidLine(0,i,[i])
		print(outcome['Common'][0])
		
		print(outcome['CalcFullTime'][0])
		self.__CalcFullTime()
		print(outcome['Common'][0])
		
		print(outcome['SortLines'][0])
		self.__SortLines()
		print(outcome['Common'][0]+outcome['SortLines'][1].format(len(self.lines_sorted)))
		input(outcome['Common'][2])

	def __GetLines(self,from_s,to_s):
		from_c=self.ticket.GetCityCode(from_s)
		to_c=self.ticket.GetCityCode(to_s)
		if False==from_c or False==to_c:
			return False
		tmp=self.ticket.GetAllTrain(date=self.date,from_s=from_c,to_s=to_c)
		self.lines.append(tmp)
		return True
		
	def __GetValidLine(self,index,train,line):
		if index+1==len(self.lines):
			line[-1]['time_wait']=[0,0]
			self.lines_sorted.append([item.copy() for item in line])
			return
		for i in self.lines[index+1]:
			time=self.__IsValidLine(train['time_end'],i['time_start'])
			if time != False:
				line[-1]['time_wait']=time
				self.__GetValidLine(index+1,i,line+[i])

	def __IsValidLine(self,pre_train,after_train):
		time=self.__CalcTime(pre_train,after_train)
		if time[0]>self.time_area:
			return False
		elif time[0]==self.time_area and time[1]>0:
			return False
		else:
			return time

	def __CalcTime(self,end,start):
		end=self.__ConvertTime(end)
		start=self.__ConvertTime(start)
		if start[1]<end[1]:
			start[0]-=1
			start[1]+=60
		if start[0]<end[0]:
			start[0]+=24
		return [start[i]-end[i] for i in range(2)]
	
	def __ConvertTime(self,time):
		time=time.split(':')
		return [int(i) for i in time]

	def __CalcFullTime(self):
		for j in self.lines_sorted:
			time=[0,0]
			for i in j:
				tmp=self.__ConvertTime(i['time_spend'])
				time=[time[k]+tmp[k]+i['time_wait'][k] for k in range(2)]
			j[-1]['time_wait']=[time[0]+int(time[1]/60),time[1]%60]

	def __SortLines(self,page_num=100):
		count=len(self.lines_sorted)
		for i in range(len(self.lines_sorted)):
			if i%page_num==0 and i>0:
				print('以上是第{0}到{1}条记录(共{2}条记录)'.format(i-page_num,i,count))
				input('请按回车键输出下一页')
			for j in range(i+1,len(self.lines_sorted)):
				if self.__IsShorter(self.lines_sorted[i][-1]['time_wait'],self.lines_sorted[j][-1]['time_wait']):
					self.lines_sorted[i],self.lines_sorted[j]=self.lines_sorted[j],self.lines_sorted[i]
			self.__DisplayOneResult(self.lines_sorted[i])

	def __IsShorter(self,time1,time2):
		if time1[0]<time2[0]:
			return False
		elif time1[0]==time2[0] and time1[1]<=time2[1]:
			return False
		return True

	def __DisplayOneResult(self,line):
		print('┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓')
		print('┃%42s┃'%'全程{0}时{1}分'.format(line[-1]['time_wait'][0],line[-1]['time_wait'][1]))
		print('┃%47s'%'┃')
		for i in range(len(line)):
			print('┃%7s'%line[i]['time_start'],'%18s'%line[i]['time_spend'],'%18s ┃'%line[i]['time_end'])
			from_s=self.ticket.GetCityName(line[i]['from'])
			to_s=self.ticket.GetCityName(line[i]['to'])
			print(self.__DisplayE(0,from_s)+self.__DisplayE(1,line[i]['name'])+self.__DisplayE(2,to_s))
			print('┃%47s'%'┃')
			if i==len(line)-1:
				break
			if i<len(line)-1 and line[i]['to']!=line[i+1]['from']:
				print('┃%14s'%'异站中转,停留{0}时{1}分'.format(line[i]['time_wait'][0],line[i]['time_wait'][1]),'%24s'%'┃')
			else:
				print('┃%11s'%'停留{0}时{1}分'.format(line[i]['time_wait'][0],line[i]['time_wait'][1]),'%31s'%'┃')
			print('┃%47s'%'┃')
		print('┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛')

	def __DisplayE(self,flag,content):
		if flag==0:
			return '┃%{0}s'.format(7-len(content))%content
		elif flag==1:
			return '%19s'%content
		elif flag==2:
			return '%14s'%''+content+' '*(6-2*len(content))+'┃'



if __name__=='__main__':
	getFastestLine=GetFastestLine(citys=input('请依次输入经过的站点(用空格隔开):\n'))
	getFastestLine.Start()
